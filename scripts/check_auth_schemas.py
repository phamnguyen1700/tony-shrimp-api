from app.schemas.auth import OtpRequest, VerifyOtpRequest
from app.schemas.auth.auth import OtpRequest


def main() -> None:
    request = OtpRequest(email="Test@Example.COM")
    print(request.email)

    verify = VerifyOtpRequest(email="test@example.com", code="123456")
    print(verify.email, verify.code)


if __name__ == "__main__":
    main()
