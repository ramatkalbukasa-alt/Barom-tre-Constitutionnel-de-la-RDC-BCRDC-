import re
from django import forms
from .models import CitizenUser, AGE_GROUP, GENDER, LOCATION_TYPE, DRC_PROVINCES


class PhoneRegistrationForm(forms.Form):
    phone_number = forms.CharField(
        max_length=20,
        label="Numéro de téléphone",
        widget=forms.TextInput(attrs={
            "placeholder": "+243 XXX XXX XXX",
            "class": "form-input",
            "inputmode": "tel",
        }),
        help_text="Format : +243 8XX XXX XXX (RDC) ou format international",
    )

    def clean_phone_number(self):
        from .services import normalize_phone_e164

        phone = self.cleaned_data["phone_number"]
        digits = re.sub(r"\D", "", phone)
        if len(digits) < 9 or len(digits) > 15:
            raise forms.ValidationError("Numéro de téléphone invalide.")
        return normalize_phone_e164(phone)


class OTPVerifyForm(forms.Form):
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        label="Code de vérification",
        widget=forms.TextInput(attrs={
            "placeholder": "000000",
            "class": "form-input text-center text-2xl tracking-widest",
            "inputmode": "numeric",
            "autocomplete": "one-time-code",
        }),
    )

    def clean_otp_code(self):
        code = self.cleaned_data["otp_code"]
        if not code.isdigit():
            raise forms.ValidationError("Le code doit contenir uniquement des chiffres.")
        return code


class CitizenProfileForm(forms.Form):
    age_group = forms.ChoiceField(
        choices=[("", "— Sélectionner —")] + AGE_GROUP.CHOICES,
        label="Tranche d'âge",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    gender = forms.ChoiceField(
        choices=[("", "— Sélectionner —")] + GENDER.CHOICES,
        label="Genre",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    location_type = forms.ChoiceField(
        choices=LOCATION_TYPE.CHOICES,
        label="Où résidez-vous ?",
        widget=forms.RadioSelect(attrs={"class": "form-radio"}),
    )
    province = forms.ChoiceField(
        choices=[("", "— Sélectionner votre province —")] + DRC_PROVINCES,
        label="Province (si RDC)",
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    country = forms.CharField(
        max_length=50,
        label="Pays de résidence (si diaspora)",
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Ex: France, Belgique, Canada…",
            "class": "form-input",
        }),
    )

    def clean(self):
        cleaned = super().clean()
        loc = cleaned.get("location_type")
        if loc == LOCATION_TYPE.NATIONAL and not cleaned.get("province"):
            raise forms.ValidationError("Veuillez sélectionner votre province.")
        if loc == LOCATION_TYPE.DIASPORA and not cleaned.get("country"):
            raise forms.ValidationError("Veuillez indiquer votre pays de résidence.")
        return cleaned
