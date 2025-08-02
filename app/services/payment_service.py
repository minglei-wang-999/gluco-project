import os
import time
import uuid
import json
import requests
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any
import secrets
import base64
from cryptography.hazmat.primitives import serialization, hashes, ciphers
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

from sqlalchemy.orm import Session

from app.schemas.subscription import PaymentRequest, PaymentStatus, WeChatPaymentParams
from app.database.subscription import PaymentRecord, Subscription
from app.services.subscription_service import SubscriptionService

import logging
logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.app_id = os.getenv("WEIXIN_APPID")
        self.mch_id = os.getenv("WEIXIN_MCH_ID")
        self.api_key = os.getenv("WEIXIN_PAY_API_KEY")
        self.api_v3_key = os.getenv("WEIXIN_PAY_API_V3_KEY")
        self.cert_serial_no = os.getenv("WEIXIN_PAY_CERT_SERIAL_NO")
        self.notify_url = os.getenv("WEIXIN_PAY_NOTIFY_URL")
        self.pub_key_id = os.getenv("WEIXIN_PUBLIC_KEY_ID")
        self.api_url = "https://api.mch.weixin.qq.com"
        self.env_id = os.getenv("WEIXIN_ENV_ID")
        self.service_name = "gluco"
        
        # Load WeChat Pay platform certificate for verifying notifications
        self.platform_cert_path = os.path.join(os.path.dirname(__file__), "../../certs/pub_key.pem")
        try:
            with open(self.platform_cert_path, "rb") as f:
                self.platform_cert = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
        except Exception as e:
            self.platform_cert = None
            logger.info(f"Failed to load WeChat Pay platform certificate: {e}")

    def _generate_prepay_id(self, user_id: str, payment_request: PaymentRequest) -> str:
        """Generate prepay_id by calling WeChat Pay API"""
        # Calculate payment amount in cents
        total_fee = int(payment_request.payment * 100)
        
        # Create out_trade_no with subscription info
        # Format: user_id_action_planid_timestamp
        timestamp = int(time.time())
        out_trade_no = f"{payment_request.action}_{payment_request.plan_id}_{timestamp}"

        # Prepare request data for WeChat Pay API
        request_data = {
            "appid": self.app_id,
            "mchid": self.mch_id,
            "description": payment_request.name,
            "out_trade_no": out_trade_no,
            "notify_url": self.notify_url,
            "amount": {
                "total": total_fee,
                "currency": "CNY"
            },
            "payer": {
                "openid": user_id
            }
        }

        # Make API request to WeChat Pay
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Wechatpay-Serial": self.pub_key_id,
            "Authorization": self._generate_authorization(request_data)
        }
        
        response = requests.post(
            f"{self.api_url}/v3/pay/transactions/jsapi",
            json=request_data,
            headers=headers
        )
        
        if response.status_code != 200:
            raise ValueError(f"Failed to create payment: {response.text}")
        
        result = response.json()
        return result["prepay_id"]

    def _generate_authorization(self, request_data: Dict[str, Any]) -> str:
        """Generate authorization header for WeChat Pay API v3.
        
        Format: WECHATPAY2-SHA256-RSA2048 mchid="",nonce_str="",timestamp="",serial_no="",signature=""
        
        The signature string format is:
        HTTP_METHOD\n
        URL_PATH\n
        TIMESTAMP\n
        NONCE\n
        BODY\n
        """
        # Get required parameters
        http_method = "POST"
        url_path = "/v3/pay/transactions/jsapi"
        timestamp = str(int(time.time()))
        nonce_str = secrets.token_hex(16)
        body = json.dumps(request_data)
        
        # Construct the signature string
        sign_string = f"{http_method}\n{url_path}\n{timestamp}\n{nonce_str}\n{body}\n"
        
        try:
            # Load the private key from environment or file
            private_key_path = os.path.join(os.path.dirname(__file__), "../../certs/apiclient_key.pem")
            with open(private_key_path, "rb") as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            
            # Sign the string using SHA256 with RSA
            signature = private_key.sign(
                sign_string.encode("utf-8"),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            # Base64 encode the signature
            signature_b64 = base64.b64encode(signature).decode("utf-8")
            
            # Construct authorization header
            auth_string = (
                'WECHATPAY2-SHA256-RSA2048 '
                f'mchid="{self.mch_id}",'
                f'nonce_str="{nonce_str}",'
                f'timestamp="{timestamp}",'
                f'serial_no="{self.cert_serial_no}",'
                f'signature="{signature_b64}"'
            )
            
            return auth_string
            
        except Exception as e:
            raise ValueError(f"Failed to generate signature: {str(e)}")

    def _generate_payment_signature(self, prepay_id: str, timestamp: str, nonce_str: str) -> str:
        """Generate payment signature for wx.requestPayment"""
        # The string to sign should be:
        # appId\ntimestamp\nnonceStr\npackage\n
        sign_str = (
            f"{self.app_id}\n"
            f"{timestamp}\n"
            f"{nonce_str}\n"
            f"prepay_id={prepay_id}\n"
        )
        
        # Load the private key from environment or file
        private_key_path = os.path.join(os.path.dirname(__file__), "../../certs/apiclient_key.pem")
        with open(private_key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
        
        # Sign the string using SHA256 with RSA
        signature = private_key.sign(
            sign_str.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        
        # Base64 encode the signature
        signature_b64 = base64.b64encode(signature).decode("utf-8")
        
        return signature_b64

    def generate_payment_info_cloud(
        self, 
        user_id: str, 
        payment_request: PaymentRequest
    ) -> WeChatPaymentParams:
        """Generate WeChat payment parameters using cloud run's simplified API"""
        # Calculate payment amount in cents
        total_fee = int(payment_request.payment * 100)
        
        # Create out_trade_no with subscription info
        # Format: action_planid_timestamp
        timestamp = int(time.time())
        out_trade_no = f"{payment_request.action}_{payment_request.plan_id}_{timestamp}"

        # Prepare request data for WeChat Pay API
        request_data = {
            "body": payment_request.name,
            "openid": user_id,
            "out_trade_no": out_trade_no,
            "sub_mch_id": self.mch_id,
            "spbill_create_ip": "127.0.0.1",  # Not required for JSAPI but API expects it
            "total_fee": total_fee,
            "env_id": self.env_id,  # Your cloud environment ID
            "callback_type": 2,  # Use cloud container callback
            "container": {
                "service": self.service_name,  # Your service name
                "path": "/payments/notify"  # Your notification endpoint
            }
        }

        # Make API request to WeChat Pay
        response = requests.post(
            "http://api.weixin.qq.com/_/pay/unifiedorder",
            json=request_data
        )
        logger.info(f"request_data: {request_data}")
        logger.info(f"response: {response}")
        if response.status_code != 200:
            raise ValueError(f"Failed to create payment: {response.text}")
        
        result = response.json()
        if result.get("errcode") != 0:
            raise ValueError(f"Failed to create payment: {result.get('errmsg')}")
            
        # Get the payment parameters from the response
        payment = result["respdata"]["payment"]
        
        # Return parameters for wx.requestPayment
        return WeChatPaymentParams(
            appId=payment["appId"],
            timeStamp=payment["timeStamp"],
            nonceStr=payment["nonceStr"],
            package=payment["package"],
            signType=payment["signType"],
            paySign=payment["paySign"]
        )

    def generate_payment_info(
        self, 
        user_id: str, 
        payment_request: PaymentRequest
    ) -> WeChatPaymentParams:
        """Generate WeChat payment parameters for a subscription action"""
        # Step 1: Get prepay_id from WeChat Pay API
        prepay_id = self._generate_prepay_id(user_id, payment_request)
        
        # Step 2: Generate parameters for wx.requestPayment
        timestamp = str(int(time.time()))
        nonce_str = uuid.uuid4().hex
        
        # Generate signature
        pay_sign = self._generate_payment_signature(prepay_id, timestamp, nonce_str)
        
        # Return parameters for wx.requestPayment
        return WeChatPaymentParams(
            appId=self.app_id,
            timeStamp=timestamp,
            nonceStr=nonce_str,
            package=f"prepay_id={prepay_id}",
            signType="RSA",
            paySign=pay_sign
        )

    def _decrypt_notification(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt notification resource data using AEAD_AES_256_GCM"""
        try:
            # Extract required fields
            algorithm = resource["algorithm"]
            nonce = resource["nonce"].encode("utf-8")
            ciphertext = resource["ciphertext"]
            associated_data = resource.get("associated_data", "").encode("utf-8") if resource.get("associated_data") else b""
            
            if algorithm != "AEAD_AES_256_GCM":
                raise ValueError(f"Unsupported encryption algorithm: {algorithm}")
            
            # Convert API v3 key to bytes (32 bytes key required for AES-256-GCM)
            key_bytes = self.api_v3_key.encode("utf-8")
            
            # Create AESGCM cipher
            aesgcm = AESGCM(key_bytes)
            
            # Decode ciphertext from base64
            ciphertext_bytes = base64.b64decode(ciphertext)
            
            # The ciphertext includes both encrypted data and a 16-byte authentication tag
            # The tag is appended to the ciphertext
            if len(ciphertext_bytes) < 16:
                raise ValueError("Invalid ciphertext length")
            
            # Decrypt the ciphertext
            plaintext_bytes = aesgcm.decrypt(
                nonce=nonce,
                data=ciphertext_bytes,
                associated_data=associated_data if associated_data else None
            )
            
            # Parse decrypted JSON data
            return json.loads(plaintext_bytes.decode("utf-8"))
            
        except Exception as e:
            raise ValueError(f"Failed to decrypt notification: {str(e)}")

    def _verify_notification_signature(
        self,
        headers: Dict[str, str],
        body: bytes
    ) -> bool:
        """Verify the signature in notification using WeChat Pay's platform certificate"""
        try:
            # Extract signature components from header with correct lowercase
            signature = headers.get("wechatpay-signature")
            timestamp = headers.get("wechatpay-timestamp")
            nonce = headers.get("wechatpay-nonce")
            
            if not all([signature, timestamp, nonce]):
                raise ValueError("Missing required signature headers")
            
            # Construct the string to verify
            message = f"{timestamp}\n{nonce}\n{body.decode('utf-8')}\n"
            
            # Verify the signature
            try:
                self.platform_cert.verify(
                    base64.b64decode(signature),
                    message.encode("utf-8"),
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
                return True
            except InvalidSignature:
                return False
                
        except Exception as e:
            raise ValueError(f"Failed to verify signature: {str(e)}")

    def handle_payment_notification(
        self,
        headers: Dict[str, str],
        body: bytes,
        notification: Dict[str, Any]
    ) -> None:
        """Handle WeChat payment notification v3"""
        # Step 1: Verify the notification signature
        if not self._verify_notification_signature(headers, body):
            raise ValueError("Invalid notification signature")
            
        # Step 2: Decrypt the resource data
        decrypted_data = self._decrypt_notification(notification["resource"])
        
        # Step 3: Process the payment result
        if notification["event_type"] != "TRANSACTION.SUCCESS":
            return  # Only process successful transactions
            
        # Extract payment details from decrypted data
        transaction_id = decrypted_data["transaction_id"]
        
        # Check if this transaction has already been processed
        existing_payment = self.db.query(PaymentRecord).filter(
            PaymentRecord.transaction_id == transaction_id
        ).first()
        
        if existing_payment:
            # If payment exists and has subscription_id, it's already been fully processed
            if existing_payment.subscription_id is not None:
                return  # Return success silently to stop further callbacks
            # If payment exists but no subscription_id, something went wrong in previous processing
            # Continue with the rest of the logic to try processing again
        
        out_trade_no = decrypted_data["out_trade_no"]
        total_fee = decrypted_data["amount"]["total"]  # Amount in cents
        trade_state = decrypted_data["trade_state"]
        user_id = decrypted_data["payer"]["openid"]
        
        if not existing_payment:
            # Create payment record only if it doesn't exist
            payment_record = PaymentRecord(
                user_id=user_id,
                subscription_id=None,  # Will be set after subscription is created
                transaction_id=transaction_id,
                amount=Decimal(total_fee) / 100,  # Convert cents to yuan
                status=PaymentStatus.SUCCESS if trade_state == "SUCCESS" else PaymentStatus.FAILED
            )
            self.db.add(payment_record)
            self.db.commit()
        else:
            payment_record = existing_payment

        if trade_state == "SUCCESS":
            # Parse subscription info from out_trade_no
            # Format: user_id_action_planid_timestamp
            parts = out_trade_no.split("_")
            action, plan_id = parts[:2]
            
            # Call update_subscription to complete the subscription update
            subscription_service = SubscriptionService(self.db)
            subscription_service.update_subscription(
                user_id=user_id,
                action=action,
                plan_id=plan_id,
                expected_payment=payment_record.amount
            )

            # Update payment record with new subscription ID
            subscription = self.db.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.plan_id == plan_id,
                Subscription.status == "active"
            ).order_by(Subscription.id.desc()).first()
            
            if subscription:
                payment_record.subscription_id = subscription.id
                self.db.commit() 


    def handle_payment_notification_cloud(
        self,
        headers: Dict[str, str],
        body: bytes,
        notification: Dict[str, Any]
    ) -> None:
        """using 开放接口服务 to handle payment notification
        https://developers.weixin.qq.com/miniprogram/dev/wxcloudservice/wxcloudrun/src/development/pay/callback/
        response:
        {
            "returnCode":"SUCCESS",
            "appid":"wxd2565e6a04246fd1",
            "mchId":"1800780001",
            "subAppid":"wxd2565e6a04246fd1",
            "subMchId":"1712734762",
            "nonceStr":"f6444fd22de27b16",
            "resultCode":"SUCCESS",
            "openid":"oPoo341Im-roYxAd3WD3D_6J-4bA",
            "isSubscribe":"N",
            "subOpenid":"oZWaC4xeOVCUkip5njeEeXi1TEsk",
            "subIsSubscribe":"N",
            "tradeType":"JSAPI",
            "bankType":"OTHERS",
            "totalFee":1,
            "feeType":"CNY",
            "cashFee":1,
            "transactionId":"4200004561202203217657282768",
            "outTradeNo":"2021WERUN1647839289398",
            "timeEnd":"20220321132007"
            }
        """
        logger.info(f"headers: {headers}")
        logger.info(f"notification: {notification}")
        # Step 1: Verify the notification signature
        if notification["returnCode"] != "SUCCESS":
            return  # Only process successful transactions
            
        # Extract payment details from decrypted data
        transaction_id = notification["transactionId"]
        
        # Check if this transaction has already been processed
        existing_payment = self.db.query(PaymentRecord).filter(
            PaymentRecord.transaction_id == transaction_id
        ).first()
        logger.info(f"existing_payment: {existing_payment}")
        if existing_payment:
            # If payment exists and has subscription_id, it's already been fully processed
            if existing_payment.subscription_id is not None:
                return  # Return success silently to stop further callbacks
            # If payment exists but no subscription_id, something went wrong in previous processing
            # Continue with the rest of the logic to try processing again
        
        out_trade_no = notification["outTradeNo"]
        total_fee = notification["totalFee"]  # Amount in cents
        result_code = notification["resultCode"]
        user_id = notification["subOpenid"]
        
        if not existing_payment:
            # Create payment record only if it doesn't exist
            payment_record = PaymentRecord(
                user_id=user_id,
                subscription_id=None,  # Will be set after subscription is created
                transaction_id=transaction_id,
                amount=Decimal(total_fee) / 100,  # Convert cents to yuan
                status=result_code
            )
            self.db.add(payment_record)
            self.db.commit()
            logger.info(f"add a new payment_record: {payment_record}")
        else:
            payment_record = existing_payment
            logger.info(f"update an existing payment_record: {payment_record}")

        if result_code == "SUCCESS":
            # Parse subscription info from out_trade_no
            # Format: user_id_action_planid_timestamp
            parts = out_trade_no.split("_")
            action, plan_id = parts[:2]
            
            # Call update_subscription to complete the subscription update
            subscription_service = SubscriptionService(self.db)
            subscription_service.update_subscription(
                user_id=user_id,
                action=action,
                plan_id=plan_id,
                expected_payment=payment_record.amount
            )

            logger.info(f"update subscription: {user_id}, {action}, {plan_id}, {payment_record.amount}")
            # Update payment record with new subscription ID
            subscription = self.db.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.plan_id == plan_id,
                Subscription.status == "active"
            ).order_by(Subscription.id.desc()).first()
            
            if subscription:
                payment_record.subscription_id = subscription.id
                self.db.commit() 
                logger.info(f"update payment_record: {payment_record}")

        logger.info(f"finished processing payment notification")