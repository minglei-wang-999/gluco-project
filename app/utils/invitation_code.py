from datetime import datetime, timedelta
import hashlib


def generate_invite_code(expire_at: datetime) -> str:
    """Generate an 8-digit invitation code based on the expiry datetime."""
    # Use only the expiry date (YYYYMMDD) for simplicity
    date_str = expire_at.strftime("%Y%m%d")
    # Hash the date string and take the first 8 digits
    hash_digest = hashlib.sha256(date_str.encode()).hexdigest()
    code_int = int(hash_digest[:8], 16) % 100_000_000
    return f"{code_int:08d}"


def verify_invite_code(invite_code: str) -> bool:
    """Verify if the invitation code is valid for today or a future date."""
    current_date = datetime.now().date()
    # Allow codes for today and any future date (not expired)
    for offset in range(0, 7):  # Allow up to 7 days in the future
        check_date = current_date + timedelta(days=offset)
        expected_code = generate_invite_code(datetime.combine(check_date, datetime.min.time()))
        if invite_code == expected_code:
            return True
    return False
