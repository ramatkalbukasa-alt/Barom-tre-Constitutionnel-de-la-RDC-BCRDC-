import random
import logging
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from .models import CitizenUser, OTPVerification

logger = logging.getLogger(__name__)


def generate_otp() -> str:
    return str(random.randint(100000, 999999))


def send_otp(phone_number: str, otp_code: str) -> bool:
    """
    Send OTP via SMS.
    In development (no AT credentials), logs to console.
    In production with AT credentials, uses Africa's Talking.
    """
    at_username = getattr(settings, "AT_USERNAME", "")
    at_api_key = getattr(settings, "AT_API_KEY", "")

    if at_username and at_api_key:
        return _send_via_africas_talking(phone_number, otp_code, at_username, at_api_key)

    return _send_mock_console(phone_number, otp_code)


def _send_mock_console(phone_number: str, otp_code: str) -> bool:
    logger.info("=" * 50)
    logger.info(f"[MOCK SMS] → {phone_number}")
    logger.info(f"[MOCK SMS] Code OTP : {otp_code}")
    logger.info(f"[MOCK SMS] Expire dans {settings.OTP_EXPIRY_MINUTES} minutes")
    logger.info("=" * 50)
    print(f"\n{'='*50}\n[BCRDC OTP] Code pour {phone_number} : {otp_code}\n{'='*50}\n")
    return True


def _send_via_africas_talking(phone_number: str, otp_code: str, username: str, api_key: str) -> bool:
    try:
        import africastalking
        africastalking.initialize(username, api_key)
        sms = africastalking.SMS
        message = f"BCRDC: Votre code de vérification est {otp_code}. Valide {settings.OTP_EXPIRY_MINUTES} min."
        response = sms.send(message, [phone_number], sender_id=settings.AT_SENDER_ID)
        logger.info(f"AT SMS response: {response}")
        return True
    except Exception as e:
        logger.error(f"Africa's Talking SMS error: {e}")
        return False


def create_otp_for_phone(phone_number: str) -> OTPVerification:
    phone_hash = CitizenUser.hash_phone(phone_number)
    OTPVerification.objects.filter(phone_hash=phone_hash, is_used=False).update(is_used=True)

    otp_code = generate_otp()
    expiry = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    otp = OTPVerification.objects.create(
        phone_hash=phone_hash,
        otp_code=otp_code,
        expires_at=expiry,
    )
    send_otp(phone_number, otp_code)
    return otp


def verify_otp(phone_number: str, code: str) -> tuple[bool, str]:
    """
    Returns (success: bool, message: str)
    """
    phone_hash = CitizenUser.hash_phone(phone_number)

    try:
        otp = OTPVerification.objects.filter(
            phone_hash=phone_hash,
            is_used=False,
        ).latest("created_at")
    except OTPVerification.DoesNotExist:
        return False, "Aucun code OTP actif. Veuillez en demander un nouveau."

    if otp.is_expired():
        return False, "Ce code OTP a expiré. Veuillez en demander un nouveau."

    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        return False, "Trop de tentatives. Veuillez demander un nouveau code."

    otp.attempts += 1
    otp.save(update_fields=["attempts"])

    if otp.otp_code != code:
        remaining = settings.OTP_MAX_ATTEMPTS - otp.attempts
        return False, f"Code incorrect. {remaining} tentative(s) restante(s)."

    otp.is_used = True
    otp.save(update_fields=["is_used"])
    return True, "Vérification réussie."


def get_or_create_citizen(phone_number: str) -> CitizenUser:
    phone_hash = CitizenUser.hash_phone(phone_number)
    user, _ = CitizenUser.objects.get_or_create(phone_hash=phone_hash)
    return user
