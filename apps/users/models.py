import hashlib
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class AGE_GROUP:
    UNDER_18 = "under_18"
    AGE_18_25 = "18_25"
    AGE_26_35 = "26_35"
    AGE_36_50 = "36_50"
    OVER_50 = "over_50"

    CHOICES = [
        (UNDER_18, "Moins de 18 ans"),
        (AGE_18_25, "18 – 25 ans"),
        (AGE_26_35, "26 – 35 ans"),
        (AGE_36_50, "36 – 50 ans"),
        (OVER_50, "Plus de 50 ans"),
    ]


class GENDER:
    MALE = "M"
    FEMALE = "F"
    OTHER = "autre"

    CHOICES = [
        (MALE, "Homme"),
        (FEMALE, "Femme"),
        (OTHER, "Autre / Préfère ne pas répondre"),
    ]


class LOCATION_TYPE:
    NATIONAL = "national"
    DIASPORA = "diaspora"

    CHOICES = [
        (NATIONAL, "RDC (national)"),
        (DIASPORA, "Diaspora (hors RDC)"),
    ]


DRC_PROVINCES = [
    ("kinshasa", "Kinshasa"),
    ("kongo_central", "Kongo Central"),
    ("kwango", "Kwango"),
    ("kwilu", "Kwilu"),
    ("mai_ndombe", "Maï-Ndombe"),
    ("kasai", "Kasaï"),
    ("kasai_central", "Kasaï Central"),
    ("kasai_oriental", "Kasaï Oriental"),
    ("lomami", "Lomami"),
    ("sankuru", "Sankuru"),
    ("maniema", "Maniema"),
    ("south_kivu", "Sud-Kivu"),
    ("north_kivu", "Nord-Kivu"),
    ("ituri", "Ituri"),
    ("haut_uele", "Haut-Uélé"),
    ("tshopo", "Tshopo"),
    ("bas_uele", "Bas-Uélé"),
    ("nord_ubangi", "Nord-Ubangi"),
    ("mongala", "Mongala"),
    ("sud_ubangi", "Sud-Ubangi"),
    ("equateur", "Équateur"),
    ("tshuapa", "Tshuapa"),
    ("tanganyika", "Tanganyika"),
    ("haut_lomami", "Haut-Lomami"),
    ("lualaba", "Lualaba"),
    ("haut_katanga", "Haut-Katanga"),
]


class CitizenUserManager(BaseUserManager):
    def create_user(self, phone_hash, **extra_fields):
        if not phone_hash:
            raise ValueError("Le hash du téléphone est obligatoire.")
        user = self.model(phone_hash=phone_hash, **extra_fields)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_hash, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        user = self.model(phone_hash=phone_hash, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user


class CitizenUser(AbstractBaseUser, PermissionsMixin):
    phone_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="Hash du téléphone",
    )
    age_group = models.CharField(
        max_length=10,
        choices=AGE_GROUP.CHOICES,
        blank=True,
        verbose_name="Tranche d'âge",
    )
    gender = models.CharField(
        max_length=10,
        choices=GENDER.CHOICES,
        blank=True,
        verbose_name="Genre",
    )
    location_type = models.CharField(
        max_length=10,
        choices=LOCATION_TYPE.CHOICES,
        blank=True,
        verbose_name="Localisation",
    )
    province = models.CharField(
        max_length=50,
        choices=DRC_PROVINCES,
        blank=True,
        verbose_name="Province",
    )
    country = models.CharField(
        max_length=50,
        blank=True,
        default="CD",
        verbose_name="Pays (diaspora)",
    )
    is_verified = models.BooleanField(default=False, verbose_name="OTP vérifié")
    has_voted = models.BooleanField(default=False, verbose_name="A voté")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CitizenUserManager()

    USERNAME_FIELD = "phone_hash"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Citoyen"
        verbose_name_plural = "Citoyens"

    def __str__(self):
        return f"Citoyen #{self.pk} ({self.get_location_type_display()})"

    @staticmethod
    def hash_phone(phone_number: str) -> str:
        normalized = "".join(filter(str.isdigit, phone_number))
        return hashlib.sha256(normalized.encode()).hexdigest()


class OTPVerification(models.Model):
    phone_hash = models.CharField(max_length=64, db_index=True, verbose_name="Hash téléphone")
    otp_code = models.CharField(max_length=6, verbose_name="Code OTP")
    is_used = models.BooleanField(default=False, verbose_name="Utilisé")
    attempts = models.PositiveSmallIntegerField(default=0, verbose_name="Tentatives")
    expires_at = models.DateTimeField(verbose_name="Expire à")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Vérification OTP"
        verbose_name_plural = "Vérifications OTP"
        ordering = ["-created_at"]

    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"OTP {self.phone_hash[:8]}… (expiré={self.is_expired()})"
