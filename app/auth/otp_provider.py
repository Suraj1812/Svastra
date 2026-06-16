import logging

logger = logging.getLogger(__name__)

MOCK_OTP = "123456"
_verified_mobiles = set()


def send_otp(mobile: str):
    logger.info("Mock OTP for %s: %s", mobile, MOCK_OTP)

    return {
        "success": True,
        "mobile_number": mobile,
        "message": "OTP sent successfully"
    }


def verify_otp(mobile: str, otp: str):
    is_valid = otp == MOCK_OTP
    if is_valid:
        _verified_mobiles.add(mobile)
    return is_valid


def is_mobile_verified(mobile: str):
    return mobile in _verified_mobiles


def consume_mobile_verification(mobile: str):
    if mobile not in _verified_mobiles:
        return False

    _verified_mobiles.remove(mobile)
    return True


def reset_verifications():
    _verified_mobiles.clear()
