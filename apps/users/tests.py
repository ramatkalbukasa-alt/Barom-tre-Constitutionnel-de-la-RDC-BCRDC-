from django.test import TestCase, override_settings

from apps.users.models import CitizenUser, OTPVerification
from apps.users import services


class PhoneHashTests(TestCase):
    def test_hash_is_normalized_and_stable(self):
        a = CitizenUser.hash_phone("+243 810 000 000")
        b = CitizenUser.hash_phone("243810000000")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)

    def test_pepper_changes_hash(self):
        with override_settings(PHONE_HASH_PEPPER="pepper-one"):
            h1 = CitizenUser.hash_phone("243810000000")
        with override_settings(PHONE_HASH_PEPPER="pepper-two"):
            h2 = CitizenUser.hash_phone("243810000000")
        self.assertNotEqual(h1, h2)


class OTPFlowTests(TestCase):
    def _latest_otp_code(self, phone: str) -> str:
        phone_hash = CitizenUser.hash_phone(phone)
        return (
            OTPVerification.objects.filter(phone_hash=phone_hash, is_used=False)
            .latest("created_at")
            .otp_code
        )

    def test_create_and_verify_success(self):
        ok, _ = services.create_otp_for_phone("243810000001")
        self.assertTrue(ok)
        code = self._latest_otp_code("243810000001")
        ok, _ = services.verify_otp("243810000001", code)
        self.assertTrue(ok)

    def test_wrong_code_fails(self):
        ok, _ = services.create_otp_for_phone("243810000002")
        self.assertTrue(ok)
        code = self._latest_otp_code("243810000002")
        wrong = "000000" if code != "000000" else "111111"
        ok, _ = services.verify_otp("243810000002", wrong)
        self.assertFalse(ok)

    def test_resend_cooldown_active(self):
        ok, _ = services.create_otp_for_phone("243810000003")
        self.assertTrue(ok)
        self.assertGreater(services.seconds_until_resend_allowed("243810000003"), 0)

    def test_no_cooldown_for_new_number(self):
        self.assertEqual(services.seconds_until_resend_allowed("243899999999"), 0)
