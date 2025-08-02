from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..dependencies import get_db
from ..models.user_models import (
    WeixinUser,
    WeixinUserCreate,
    WeixinUserResponse,
    WeixinLoginRequest,
)
from ..utils.auth import create_access_token
from ..utils.weixin_auth import get_weixin_openid
from ..services.subscription_service import SubscriptionService
from datetime import timedelta
import os
import logging
from ..utils.invitation_code import verify_invite_code

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/weixin/auth", tags=["weixin_auth"])

@router.post("/login", response_model=dict)
async def weixin_login(login_data: WeixinLoginRequest, db: Session = Depends(get_db)):
    """Login or register WeChat user using code from WeChat mini program."""
    try:
        logger.info(f"WeChat login attempt with code: {login_data.code}")
        logger.info(f"WEIXIN_APPID: {os.getenv('WEIXIN_APPID')}")
        logger.info(
            f"WEIXIN_SECRET length: {len(os.getenv('WEIXIN_SECRET', ''))} chars"
        )

        # Get openid from WeChat using the code
        openid = await get_weixin_openid(login_data.code)
        logger.info(f"Got openid response: {openid}")

        if not openid:
            logger.error("Failed to get openid from WeChat")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid WeChat code"
            )

        # Check if user exists
        user = db.query(WeixinUser).filter(WeixinUser.openid == openid).first()
        logger.info(f"Existing user found: {user is not None}")

        # If user doesn't exist, create new user
        is_new_user = False
        if not user:
            # if login_data.invite_code is None:
            #     raise HTTPException(
            #         status_code=status.HTTP_400_BAD_REQUEST, detail="Invite code is required"
            #     )
            # invite_code = login_data.invite_code
            # if not verify_invite_code(invite_code):
            #     raise HTTPException(
            #         status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid invite code"
            #     )
            user = WeixinUser(openid=openid)
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info("Created new user")
            is_new_user = True

        # Initialize subscription service
        subscription_service = SubscriptionService(db)

        # Create trial subscription for new users or existing users without subscription history
        if is_new_user or not subscription_service.has_subscription_history(user.openid):
            subscription_service.create_trial_subscription(user.openid)
            logger.info("Created trial subscription for user")

        # Create access token
        access_token = create_access_token(
            data={"sub": f"weixin:{openid}"},
            expires_delta=timedelta(days=30),  # WeChat tokens can last longer
        )
        logger.info("Created access token")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": WeixinUserResponse.model_validate(user).model_dump(),
        }

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.put("/profile", response_model=WeixinUserResponse)
async def update_weixin_profile(
    user_data: WeixinUserCreate, db: Session = Depends(get_db)
):
    """Update WeChat user profile."""
    try:
        user = (
            db.query(WeixinUser).filter(WeixinUser.openid == user_data.openid).first()
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Update user profile
        user.nickname = user_data.nickname
        user.avatar_url = user_data.avatar_url

        db.commit()
        db.refresh(user)

        return user

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
