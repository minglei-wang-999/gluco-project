from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    """Schema for user creation."""

    password: str


class Token(BaseModel):
    """Schema for authentication token."""

    access_token: str
    token_type: str


class EmailSchema(BaseModel):
    """Schema for email operations."""

    email: EmailStr
