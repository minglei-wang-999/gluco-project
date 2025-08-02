from sqlalchemy import Column, Integer, String, DateTime, Boolean, text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pydantic import BaseModel, EmailStr, constr, ConfigDict
from datetime import datetime
from app.database.database import Base
from typing import Optional


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    activation_token = Column(String(100), unique=True, nullable=True)
    full_name = Column(String(100), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )

    # Use string references for relationships to avoid circular imports
    nutrition_records = relationship("NutritionRecord", back_populates="user")
    tasks = relationship("Task", back_populates="user")


class WeixinUser(Base):
    __tablename__ = "weixin_users"

    id = Column(Integer, primary_key=True, index=True)
    openid = Column(String(100), unique=True, index=True, nullable=False)
    nickname = Column(String(100), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )

    # Use string references for relationships to avoid circular imports
    nutrition_records = relationship("NutritionRecord", back_populates="weixin_user")
    tasks = relationship("Task", back_populates="weixin_user")


# Pydantic models for request/response
class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    password: constr(min_length=8)


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: str | None = None
    exp: datetime | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class WeixinUserBase(BaseModel):
    openid: str
    nickname: str | None = None
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class WeixinUserCreate(WeixinUserBase):
    pass


class WeixinUserResponse(WeixinUserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class WeixinLoginRequest(BaseModel):
    code: str
    invite_code: Optional[str] = None
