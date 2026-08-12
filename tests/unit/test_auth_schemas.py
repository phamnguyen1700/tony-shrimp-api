import pytest
from pydantic import ValidationError

from app.schemas.auth import OtpRequest, VerifyOtpRequest


def test_otp_request_accepts_valid_email() -> None:
    request = OtpRequest(email="User@example.com")

    assert str(request.email) == "User@example.com"


def test_otp_request_rejects_invalid_email() -> None:
    with pytest.raises(ValidationError):
        OtpRequest(email="not-an-email")


@pytest.mark.parametrize("code", ["12345", "1234567"])
def test_verify_otp_rejects_wrong_code_length(code: str) -> None:
    with pytest.raises(ValidationError):
        VerifyOtpRequest(email="user@example.com", code=code)


def test_verify_otp_accepts_six_character_code() -> None:
    request = VerifyOtpRequest(email="user@example.com", code="123456")

    assert str(request.email) == "user@example.com"
    assert request.code == "123456"
