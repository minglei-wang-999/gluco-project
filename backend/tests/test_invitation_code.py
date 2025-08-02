import pytest
from datetime import datetime, timedelta
from app.utils.invitation_code import generate_invite_code, verify_invite_code

class TestInvitationCode:
    def test_generate_and_verify_valid_code(self):
        expire_at = datetime.now() + timedelta(days=1)
        code = generate_invite_code(expire_at)
        assert verify_invite_code(code) is True

    def test_verify_expired_code(self):
        expire_at = datetime.now() - timedelta(days=10)
        code = generate_invite_code(expire_at)
        assert verify_invite_code(code) is False

    def test_generate_and_verify_code_for_today(self):
        expire_at = datetime.now()
        code = generate_invite_code(expire_at)
        assert verify_invite_code(code) is True

    def test_generate_and_verify_code_for_future_date(self):
        expire_at = datetime.now() + timedelta(days=6)
        code = generate_invite_code(expire_at)
        print(code)
        assert verify_invite_code(code) is True

    def test_invalid_code(self):
        assert verify_invite_code("00000000") is False
