from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit
from .forms import PhoneRegistrationForm, OTPVerifyForm, CitizenProfileForm
from .services import (
    create_otp_for_phone,
    verify_otp,
    get_or_create_citizen,
    seconds_until_resend_allowed,
    get_otp_for_ui,
    sms_uses_mock,
)


def _verify_otp_context(phone: str, form) -> dict:
    return {
        "form": form,
        "phone": phone,
        "dev_otp_code": get_otp_for_ui(phone),
        "otp_expiry": settings.OTP_EXPIRY_MINUTES,
        "sms_mock": sms_uses_mock(),
    }


def home(request):
    return render(request, "home.html")


@ratelimit(key="ip", rate="5/h", method="POST", block=False)
@require_http_methods(["GET", "POST"])
def register_phone(request):
    if request.method == "POST":
        if getattr(request, "limited", False):
            messages.error(request, "Trop de demandes de code. Réessayez dans une heure.")
            return redirect("users:register")
        form = PhoneRegistrationForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data["phone_number"]
            ok, err = create_otp_for_phone(phone)
            if not ok:
                messages.error(request, err)
                return render(request, "users/register.html", {"form": form})
            request.session["pending_phone"] = phone
            if sms_uses_mock():
                messages.success(request, "Code genere. Saisissez-le ci-dessous.")
            else:
                messages.success(request, "Code OTP envoye. Verifiez votre telephone.")
            return redirect("users:verify_otp")
    else:
        form = PhoneRegistrationForm()
    return render(request, "users/register.html", {"form": form})


@ratelimit(key="ip", rate="10/h", method="POST", block=False)
@require_http_methods(["GET", "POST"])
def verify_otp_view(request):
    phone = request.session.get("pending_phone")
    if not phone:
        return redirect("users:register")

    if request.method == "POST":
        if getattr(request, "limited", False):
            messages.error(request, "Trop de tentatives. Réessayez plus tard.")
            return redirect("users:verify_otp")
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["otp_code"]
            success, message = verify_otp(phone, code)
            if success:
                user = get_or_create_citizen(phone)
                user.is_verified = True
                user.save(update_fields=["is_verified"])
                request.session["verified_user_id"] = user.pk
                request.session["pending_phone"] = None
                return redirect("users:complete_profile")
            else:
                messages.error(request, message)
    else:
        form = OTPVerifyForm()

    return render(request, "users/verify_otp.html", _verify_otp_context(phone, form))


@ratelimit(key="ip", rate="5/h", method=["GET", "POST"], block=False)
@require_http_methods(["GET", "POST"])
def resend_otp(request):
    phone = request.session.get("pending_phone")
    if not phone:
        return redirect("users:register")

    if getattr(request, "limited", False):
        messages.error(request, "Trop de demandes de code. Réessayez plus tard.")
        return redirect("users:verify_otp")

    wait = seconds_until_resend_allowed(phone)
    if wait > 0:
        messages.warning(request, f"Veuillez patienter {wait} seconde(s) avant de redemander un code.")
        return redirect("users:verify_otp")

    ok, err = create_otp_for_phone(phone)
    if not ok:
        messages.error(request, err)
        return redirect("users:verify_otp")
    messages.info(request, "Un nouveau code vous a ete envoye." if not sms_uses_mock() else "Un nouveau code a ete genere.")
    return redirect("users:verify_otp")


@require_http_methods(["GET", "POST"])
def complete_profile(request):
    user_id = request.session.get("verified_user_id")
    if not user_id:
        return redirect("users:register")

    try:
        from .models import CitizenUser
        user = CitizenUser.objects.get(pk=user_id)
    except CitizenUser.DoesNotExist:
        return redirect("users:register")

    if user.has_voted:
        messages.info(request, "Vous avez déjà participé à la consultation.")
        return redirect("consultation:dashboard")

    if request.method == "POST":
        form = CitizenProfileForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            user.age_group = d["age_group"]
            user.gender = d["gender"]
            user.location_type = d["location_type"]
            user.province = d.get("province", "")
            user.country = d.get("country", "CD")
            user.save(update_fields=["age_group", "gender", "location_type", "province", "country"])
            return redirect("consultation:vote")
    else:
        form = CitizenProfileForm()

    return render(request, "users/profile.html", {"form": form})
