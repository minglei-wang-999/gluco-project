"""Email utility functions using Resend."""
import os
import logging
import resend
from typing import Optional

logger = logging.getLogger(__name__)


def get_resend_client() -> bool:
    """Configure Resend client if API key is available."""
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        logger.warning("Resend API key not found in environment variables")
        return False
    resend.api_key = api_key
    return True


def get_frontend_url() -> str:
    """Get the frontend URL from environment variables."""
    return os.getenv("FRONTEND_URL", "http://localhost:3000")


async def send_activation_email(email: str, activation_token: str) -> bool:
    """Send activation email to user."""
    if not get_resend_client():
        logger.warning(
            f"Email not sent to {email} - Resend configuration not available"
        )
        return False

    # Get the frontend URL and construct the activation link
    frontend_url = get_frontend_url()
    activation_link = f"{frontend_url}/activate?token={activation_token}"

    try:
        response = resend.Emails.send(
            {
                "from": os.getenv("MAIL_FROM", "onboarding@resend.dev"),
                "to": email,
                "subject": "Activate Your Account",
                "html": f"""
                <h1>Welcome to Gluco!</h1>
                <p>Please click the link below to activate your account:</p>
                <p><a href="{activation_link}">Activate Account</a></p>
                <p>If you didn't request this email, you can safely ignore it.</p>
                <p>This link will expire in 24 hours.</p>
            """,
            }
        )
        return True if response else False
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {str(e)}")
        return False
