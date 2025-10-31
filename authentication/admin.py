from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    User,
    UserSession,
    PhoneOTP,
    EmailOTP,
    OTPAttempt,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model."""

    fieldsets = (
        (None, {
            "fields": (
                "username",
                "password",
            )
        }),
        ("Personal info", {
            "fields": (
                "first_name",
                "last_name",
                "email",
                "phone_number",
                "profile_picture",
            )
        }),
        ("Permissions", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        ("Important dates", {
            "fields": (
                "last_login",
                "date_joined",
                "created_at",
                "updated_at",
            )
        }),
        ("Verification", {
            "fields": (
                "descope_user_id",
                "is_verified",
                "is_phone_verified",
            )
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username",
                "email",
                "phone_number",
                "password1",
                "password2",
                "is_staff",
                "is_superuser",
            ),
        }),
    )

    list_display = (
        "id",
        "username",
        "email",
        "phone_number",
        "is_verified",
        "is_phone_verified",
        "is_staff",
        "is_superuser",
        "created_at",
    )
    list_filter = ("is_staff", "is_superuser", "is_verified", "is_phone_verified", "created_at")
    search_fields = ("username", "email", "phone_number")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "last_login", "date_joined")


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "is_active",
        "expires_at",
        "created_at",
    )
    list_filter = ("is_active", "expires_at", "created_at")
    search_fields = ("user__username", "user__email", "session_token")
    readonly_fields = ("created_at",)


@admin.register(PhoneOTP)
class PhoneOTPAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "phone_number",
        "otp_code",
        "is_verified",
        "attempts",
        "max_attempts",
        "expires_at",
        "created_at",
    )
    list_filter = ("is_verified", "created_at")
    search_fields = ("phone_number", "otp_code")
    readonly_fields = ("created_at",)


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "email",
        "otp_code",
        "is_verified",
        "attempts",
        "max_attempts",
        "expires_at",
        "created_at",
    )
    list_filter = ("is_verified", "created_at")
    search_fields = ("email", "otp_code")
    readonly_fields = ("created_at",)


@admin.register(OTPAttempt)
class OTPAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "identifier",
        "attempt_type",
        "attempts_count",
        "is_blocked",
        "blocked_until",
        "last_attempt",
        "created_at",
    )
    list_filter = ("attempt_type", "is_blocked", "created_at")
    search_fields = ("identifier",)
    readonly_fields = ("created_at",)
