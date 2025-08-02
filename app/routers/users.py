import logging
from fastapi import APIRouter, HTTPException
from ..models.user_models import User, UserCreate, UserResponse, Token, UserLogin
from ..utils.auth import get_password_hash, authenticate_user, create_access_token
from ..utils.email import send_activation_email
from ..dependencies import get_db, get_current_user
from sqlalchemy.orm import Session
from fastapi import Depends, BackgroundTasks
from fastapi import status
import secrets
import traceback
from datetime import timedelta
from ..utils.auth import ACCESS_TOKEN_EXPIRE_MINUTES
from ..services.subscription_service import SubscriptionService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user: UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """Register a new user."""
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Generate activation token
    activation_token = secrets.token_urlsafe(32)

    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        is_active=False,
        activation_token=activation_token,
    )

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # Initialize subscription service
        subscription_service = SubscriptionService(db)

        # Create trial subscription for new user (they won't have any history since they just registered)
        subscription_service.create_trial_subscription(str(db_user.id))
        logger.info("Created trial subscription for new user")

        # Send activation email in the background
        background_tasks.add_task(
            send_activation_email, db_user.email, activation_token
        )

        return db_user
    except Exception as e:
        db.rollback()
        logger.error(f"Error registering user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not register user",
        )


@router.post("/login", response_model=Token)
async def login(user: UserLogin, db: Session = Depends(get_db)):
    """Login user and return access token."""
    try:
        logger.info(f"Login attempt for email: {user.email}")

        # Try to authenticate user
        try:
            user_obj = authenticate_user(user.email, user.password, db)
            if not user_obj:
                logger.warning(
                    f"Failed login attempt for email: {user.email} - Invalid credentials"
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except Exception as auth_error:
            logger.error(f"Authentication error for {user.email}: {str(auth_error)}")
            logger.error(f"Authentication traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Authentication failed: {str(auth_error)}",
            )

        # Try to create access token
        try:
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user_obj.email}, expires_delta=access_token_expires
            )
            logger.info(f"Successfully created access token for user: {user.email}")
            return Token(access_token=access_token)
        except Exception as token_error:
            logger.error(f"Token creation error for {user.email}: {str(token_error)}")
            logger.error(f"Token creation traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create access token: {str(token_error)}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected login error for {user.email}: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}",
        )


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.post("/activate/{token}", response_model=UserResponse, tags=["users"])
async def activate_user(token: str, db: Session = Depends(get_db)):
    """Activate a user account using the activation token."""
    # Find user by activation token
    user = db.query(User).filter(User.activation_token == token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid activation token"
        )

    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Account already activated"
        )

    # Activate user and clear token
    user.is_active = True
    user.activation_token = None

    try:
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        logger.error(f"Error activating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not activate user",
        )
