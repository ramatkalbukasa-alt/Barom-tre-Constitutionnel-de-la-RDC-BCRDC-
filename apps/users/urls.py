from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    path("", views.home, name="home"),
    path("participer/", views.register_phone, name="register"),
    path("participer/verifier/", views.verify_otp_view, name="verify_otp"),
    path("participer/renvoyer/", views.resend_otp, name="resend_otp"),
    path("participer/profil/", views.complete_profile, name="complete_profile"),
]
