from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from .forms import PhoneRegistrationForm, OTPVerifyForm, CitizenProfileForm
from .services import create_otp_for_phone, verify_otp, get_or_create_citizen


def home(request):
    return render(request, "home.html")


@require_http_methods(["GET", "POST"])
def register_phone(request):
    if request.method == "POST":
        form = PhoneRegistrationForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data["phone_number"]
            create_otp_for_phone(phone)
            request.session["pending_phone"] = phone
            messages.success(request, "Code OTP envoyé. Vérifiez votre téléphone.")
            return redirect("users:verify_otp")
    else:
        form = PhoneRegistrationForm()
    return render(request, "users/register.html", {"form": form})


@require_http_methods(["GET", "POST"])
def verify_otp_view(request):
    phone = request.session.get("pending_phone")
    if not phone:
        return redirect("users:register")

    if request.method == "POST":
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

    return render(request, "users/verify_otp.html", {"form": form, "phone": phone})


@require_http_methods(["GET", "POST"])
def resend_otp(request):
    phone = request.session.get("pending_phone")
    if not phone:
        return redirect("users:register")
    create_otp_for_phone(phone)
    messages.info(request, "Un nouveau code OTP vous a été envoyé.")
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
