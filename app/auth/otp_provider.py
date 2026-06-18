from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import RLock

from app.config import settings


@dataclass
class _Challenge:
    expires_at: datetime
    sent_at: datetime
    attempts: int = 0
    consumed: bool = False


_challenges: dict[str, _Challenge] = {}
_verified_mobiles: set[str] = set()
_lock = RLock()


def _now():
    return datetime.now(timezone.utc)


def send_otp(mobile: str):
    now = _now()
    with _lock:
        existing = _challenges.get(mobile)
        if (
            existing is not None
            and not existing.consumed
            and now - existing.sent_at < timedelta(seconds=settings.otp_resend_cooldown_seconds)
        ):
            retry_after = settings.otp_resend_cooldown_seconds - int(
                (now - existing.sent_at).total_seconds()
            )
            return {
                "success": False,
                "mobile_number": mobile,
                "otp_sent": False,
                "expires_in_seconds": max(0, int((existing.expires_at - now).total_seconds())),
                "retry_after_seconds": max(1, retry_after),
            }

        _challenges[mobile] = _Challenge(
            sent_at=now,
            expires_at=now + timedelta(seconds=settings.otp_ttl_seconds),
        )

    return {
        "success": True,
        "mobile_number": mobile,
        "otp_sent": True,
        "expires_in_seconds": settings.otp_ttl_seconds,
        "retry_after_seconds": settings.otp_resend_cooldown_seconds,
    }


def verify_otp(mobile: str, otp: str):
    now = _now()
    with _lock:
        challenge = _challenges.get(mobile)
        if challenge is None or challenge.consumed or challenge.expires_at <= now:
            return False
        if challenge.attempts >= settings.otp_max_attempts:
            return False

        challenge.attempts += 1
        if otp != settings.mock_otp:
            return False

        challenge.consumed = True
        _verified_mobiles.add(mobile)
        return True


def is_mobile_verified(mobile: str):
    return mobile in _verified_mobiles


def consume_mobile_verification(mobile: str):
    with _lock:
        if mobile not in _verified_mobiles:
            return False
        _verified_mobiles.remove(mobile)
        return True


def reset_verifications():
    with _lock:
        _challenges.clear()
        _verified_mobiles.clear()
