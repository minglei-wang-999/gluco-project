from app.database.database import SessionLocal
from fastapi import Depends, HTTPException, status, Security
from jose import JWTError
from sqlalchemy.orm import Session
from typing import Union
from .models.user_models import User, WeixinUser
from .utils.auth import decode_access_token, oauth2_scheme
from .utils.gpt_client import GPTClient
from .storage.weixin_cloud_storage import WeixinCloudStorage
import os

# from .database.database import get_db


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    token: str = Security(oauth2_scheme), db: Session = Depends(get_db)
) -> Union[User, WeixinUser]:
    """Get the current user from the token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        user_id = decode_access_token(token)
        if user_id is None:
            raise credentials_exception
        if user_id.startswith("weixin"):
            user_id = user_id[7:]
            user = db.query(WeixinUser).filter(WeixinUser.openid == user_id).first()
            if user is None:
                raise credentials_exception
            return user
        else:
            user_id = int(user_id)
            user = db.query(User).filter(User.id == user_id).first()
            if user is None:
                raise credentials_exception
            return user
    except JWTError:
        raise credentials_exception


def get_gpt_client() -> GPTClient:
    """Dependency provider for GPTClient"""
    return GPTClient()


def get_storage() -> WeixinCloudStorage:
    """Dependency provider for WeixinCloudStorage"""
    return WeixinCloudStorage(
        app_id=os.getenv("WEIXIN_APPID"),
        app_secret=os.getenv("WEIXIN_SECRET"),
        env_id=os.getenv("WEIXIN_ENV_ID"),
        verify_ssl=False,  # Disable SSL verification in production
    )
