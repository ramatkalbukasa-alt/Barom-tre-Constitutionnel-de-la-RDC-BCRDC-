"""
Teste le flux OTP en mode mock (aucun SMS reel n'est envoye).

Usage:
    python scripts/test_sms.py +243810000000

Le code est journalise et, sur le site, affiche directement sur la page de
verification. Ce script verifie la normalisation du numero et la generation
d'un code OTP de bout en bout.
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from apps.users.services import (
    normalize_phone_e164,
    create_otp_for_phone,
    get_otp_for_ui,
)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_sms.py +243810000000")
        sys.exit(1)

    phone_raw = sys.argv[1]
    phone = normalize_phone_e164(phone_raw)
    print(f"Numero normalise : {phone}")
    print("Mode SMS         : MOCK (aucun envoi reel)")
    print()

    ok, err = create_otp_for_phone(phone_raw)
    if not ok:
        print(f"[ECHEC] {err}")
        sys.exit(1)

    code = get_otp_for_ui(phone_raw)
    print(f"[OK] Code OTP genere (affiche sur l'interface) : {code}")


if __name__ == "__main__":
    main()
