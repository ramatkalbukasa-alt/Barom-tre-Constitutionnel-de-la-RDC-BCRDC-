import random
import re
import logging
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from .models import CitizenUser, OTPVerification

logger = logging.getLogger(__name__)


def normalize_phone_e164(phone_number: str) -> str:
    """Convertit un numéro saisi en format international +243…"""
    digits = re.sub(r"\D", "", phone_number)
    if digits.startswith("243"):
        return f"+{digits}"
    if digits.startswith("0") and len(digits) >= 10:
        return f"+243{digits[1:]}"
    if len(digits) == 9:
        return f"+243{digits}"
    if phone_number.strip().startswith("+"):
        return f"+{digits}"
    return f"+{digits}"


def generate_otp() -> str:
    return str(random.randint(100000, 999999))


def sms_uses_mock() -> bool:
    """L'envoi SMS est toujours simulé (mode mock console). Le code OTP est
    affiché directement sur l'interface web de vérification."""
    return True


def get_otp_for_ui(phone_number: str) -> str | None:
    """Code OTP à afficher à l'écran (mode mock : le SMS n'est pas réellement envoyé)."""
    phone_hash = CitizenUser.hash_phone(phone_number)
    try:
        otp = OTPVerification.objects.filter(
            phone_hash=phone_hash,
            is_used=False,
        ).latest("created_at")
    except OTPVerification.DoesNotExist:
        return None
    if otp.is_expired():
        return None
    return otp.otp_code


def send_otp(phone_number: str, otp_code: str) -> tuple[bool, str]:
    """Mode mock : aucun SMS réel n'est envoyé. Le code est journalisé et affiché
    sur la page de vérification. Retourne toujours (True, "").
    """
    logger.info("[MOCK SMS] → %s | code OTP : %s", phone_number, otp_code)
    return True, ""


def create_otp_for_phone(phone_number: str) -> tuple[bool, str]:
    """
    Crée un OTP et tente l'envoi SMS.
    Retourne (succès, message_erreur_ou_vide).
    """
    phone_e164 = normalize_phone_e164(phone_number)
    phone_hash = CitizenUser.hash_phone(phone_number)
    OTPVerification.objects.filter(phone_hash=phone_hash, is_used=False).update(is_used=True)

    otp_code = generate_otp()
    expiry = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
    otp = OTPVerification.objects.create(
        phone_hash=phone_hash,
        otp_code=otp_code,
        expires_at=expiry,
    )

    send_otp(phone_e164, otp_code)
    return True, ""


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


def seconds_until_resend_allowed(phone_number: str) -> int:
    """How many seconds the user must wait before a new OTP can be sent.

    Prevents SMS flooding / cost abuse via repeated resends.
    """
    phone_hash = CitizenUser.hash_phone(phone_number)
    last = (
        OTPVerification.objects.filter(phone_hash=phone_hash)
        .order_by("-created_at")
        .first()
    )
    if not last:
        return 0
    cooldown = getattr(settings, "OTP_RESEND_COOLDOWN_SECONDS", 60)
    elapsed = (timezone.now() - last.created_at).total_seconds()
    return max(0, int(cooldown - elapsed))
