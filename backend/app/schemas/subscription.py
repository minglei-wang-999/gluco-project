from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    FUTURE = "future"  # For paid renewals that start after current subscription expires
    PENDING = "pending"  # For subscriptions awaiting payment
    EXPIRED = "expired"
    INACTIVE = "inactive"


class PaymentStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


class SubscriptionAction(BaseModel):
    action: str = Field(..., description="Type of action: renewal or upgrade")
    plan_id: str = Field(..., description="ID of the plan")
    name: str = Field(..., description="Name of the plan")
    price: Decimal = Field(..., description="Original price of the plan")
    duration: int = Field(..., description="Duration in days")
    description: List[str] = Field(..., description="List of plan features/description")
    credit: Decimal = Field(..., description="Credit from current plan if applicable")
    payment: Decimal = Field(..., description="Final payment amount after credit")


class PendingSubscription(BaseModel):
    plan_id: str
    plan_name: str
    expires_at: datetime


class SubscriptionStatusResponse(BaseModel):
    status: SubscriptionStatus
    plan_id: Optional[str] = None
    plan_name: Optional[str] = None
    start_date: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    next_expires_at: Optional[datetime] = None
    available_actions: List[SubscriptionAction]


class UpdateSubscriptionRequest(BaseModel):
    action: str = Field(..., description="Type of action: renewal or upgrade")
    plan_id: str = Field(..., description="ID of the plan to subscribe to")
    payment: Decimal = Field(..., description="Expected payment amount")


class WeChatPaymentResponse(BaseModel):
    prepay_id: str
    nonce_str: str
    timestamp: str
    sign_type: str
    pay_sign: str


class WeChatPaymentNotification(BaseModel):
    """WeChat payment notification schema for v3 API"""
    id: str = Field(..., description="通知的唯一ID")
    create_time: str = Field(..., description="通知创建时间")
    event_type: str = Field(..., description="通知类型")
    resource_type: str = Field(..., description="通知数据类型")
    summary: str = Field(..., description="通知简要说明")
    resource: Dict[str, Any] = Field(..., description="通知资源数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "EV-2018022511223320873",
                "create_time": "2015-05-20T13:29:35+08:00",
                "event_type": "TRANSACTION.SUCCESS",
                "resource_type": "encrypt-resource",
                "summary": "支付成功",
                "resource": {
                    "original_type": "transaction",
                    "algorithm": "AEAD_AES_256_GCM",
                    "ciphertext": "...",
                    "associated_data": "",
                    "nonce": "..."
                }
            }
        }


class PaymentRequest(BaseModel):
    action: str = Field(..., description="Type of action: renewal or upgrade")
    plan_id: str = Field(..., description="ID of the plan to subscribe to")
    name: str = Field(..., description="Name of the plan")
    price: Decimal = Field(..., description="Original price of the plan")
    duration: int = Field(..., description="Duration in days")
    description: List[str] = Field(..., description="List of plan features/description")
    credit: Decimal = Field(..., description="Credit from current plan if applicable")
    payment: Decimal = Field(..., description="Final payment amount after credit")


# Response for frontend to call wx.requestPayment
class WeChatPaymentParams(BaseModel):
    appId: str = Field(..., description="小程序ID")
    timeStamp: str = Field(..., description="时间戳")
    nonceStr: str = Field(..., description="随机字符串")
    package: str = Field(..., description="订单详情扩展字符串，格式为prepay_id=***")
    signType: str = Field(..., description="签名方式，默认为RSA")
    paySign: str = Field(..., description="签名") 