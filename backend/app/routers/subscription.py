from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from typing import Union, Dict, Any
import json
import logging
from app.dependencies import get_db, get_current_user
from app.models.user_models import User, WeixinUser
from app.schemas.subscription import (
    SubscriptionStatusResponse,
    UpdateSubscriptionRequest,
    WeChatPaymentNotification,
    PaymentRequest,
    WeChatPaymentParams
)
from app.services.subscription_service import SubscriptionService
from app.services.payment_service import PaymentService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["subscriptions"])

@router.get("/subscriptions/status", response_model=SubscriptionStatusResponse)
def get_subscription_status(
    db: Session = Depends(get_db),
    current_user: Union[User, WeixinUser] = Depends(get_current_user)
):
    """Get subscription status and available actions for current user"""
    user_id = str(current_user.id) if isinstance(current_user, User) else current_user.openid
    service = SubscriptionService(db)
    try:
        status = service.get_subscription_status(user_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/subscriptions/update", response_model=SubscriptionStatusResponse)
def update_subscription(
    request: UpdateSubscriptionRequest,
    db: Session = Depends(get_db),
    current_user: Union[User, WeixinUser] = Depends(get_current_user)
):
    """Create a new subscription, renewal, or upgrade"""
    user_id = str(current_user.id) if isinstance(current_user, User) else current_user.openid
    service = SubscriptionService(db)
    try:
        service.update_subscription(
            user_id=user_id,
            action=request.action,
            plan_id=request.plan_id,
            expected_payment=request.payment
        )

        current_subscription = service.get_subscription_status(user_id)
        return current_subscription
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/payments/notify")
async def handle_payment_notification(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle WeChat payment notification v3 API"""
    # Get the raw request body
    body = await request.body()
    logger.info(f"body: {body}")
    
    try:
        notification = await request.json()
        logger.info(f"notification: {notification}")
        # Process the notification
        service = PaymentService(db)
        service.handle_payment_notification_cloud(
            headers=dict(request.headers),
            body=body,
            notification=notification
        )
        
        # Return success response in required format
        return Response(
            content=json.dumps({
                "code": "SUCCESS",
                "message": "成功"
            }),
            media_type="application/json"
        )
        
    except ValueError as e:
        # Return error response in required format
        return Response(
            content=json.dumps({
                "code": "FAIL",
                "message": str(e)
            }),
            media_type="application/json",
            status_code=400
        )
    except Exception as e:
        # Return error response in required format
        return Response(
            content=json.dumps({
                "code": "FAIL",
                "message": "Internal server error"
            }),
            media_type="application/json",
            status_code=500
        )


@router.post("/subscriptions/payment", response_model=WeChatPaymentParams)
def generate_payment(
    request: Request,
    payment_request: PaymentRequest,
    db: Session = Depends(get_db),
    current_user: Union[User, WeixinUser] = Depends(get_current_user)
):
    """Generate WeChat payment parameters for a subscription action"""
    user_id = str(current_user.id) if isinstance(current_user, User) else current_user.openid
    service = PaymentService(db)
    try:
        payment_params = service.generate_payment_info_cloud(
            user_id=user_id,
            payment_request=payment_request
        )
        return payment_params
    except ValueError as e:
        logger.info(f"Failed to generate payment info: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.info(f"Failed to generate payment info: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 