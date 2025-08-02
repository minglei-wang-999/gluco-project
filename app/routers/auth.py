from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..dependencies import get_db
from ..models.user_models import User
from ..schemas.user_schemas import EmailSchema
from ..utils.email import send_activation_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/resend-activation", response_model=dict)
async def resend_activation_email(
    email_data: EmailSchema, db: Session = Depends(get_db)
):
    """Resend activation email to user"""
    user = db.query(User).filter(User.email == email_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Account already activated"
        )

    if not user.activation_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No activation token found"
        )

    await send_activation_email(email_data.email, user.activation_token)
    return {"message": "Activation email sent successfully"}
