from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CitizenUser, OTPVerification


@admin.register(CitizenUser)
class CitizenUserAdmin(UserAdmin):
    list_display = ("id", "phone_hash_preview", "age_group", "gender", "location_type", "province", "is_verified", "has_voted", "created_at")
    list_filter = ("location_type", "province", "age_group", "gender", "is_verified", "has_voted")
    search_fields = ("phone_hash",)
    ordering = ("-created_at",)
    readonly_fields = ("phone_hash", "created_at")

    fieldsets = (
        (None, {"fields": ("phone_hash", "is_verified", "has_voted")}),
        ("Profil", {"fields": ("age_group", "gender", "location_type", "province", "country")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Dates", {"fields": ("created_at",)}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone_hash",),
        }),
    )

    def phone_hash_preview(self, obj):
        return f"{obj.phone_hash[:12]}…"
    phone_hash_preview.short_description = "Hash téléphone"


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ("id", "phone_hash_preview", "is_used", "attempts", "expires_at", "created_at")
    list_filter = ("is_used",)
    readonly_fields = ("phone_hash", "otp_code", "created_at")

    def phone_hash_preview(self, obj):
        return f"{obj.phone_hash[:12]}…"
    phone_hash_preview.short_description = "Hash téléphone"
