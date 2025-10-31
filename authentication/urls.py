from django.urls import path
from . import views

urlpatterns = [
    # Authentication endpoints
    path('register/', views.UserRegistrationView.as_view(), name='user-register'),
    path('login/', views.UserLoginView.as_view(), name='user-login'),
    path('logout/', views.UserLogoutView.as_view(), name='user-logout'),
    
    # Phone OTP authentication endpoints
    path('phone/request-otp/', views.PhoneOTPRequestView.as_view(), name='phone-request-otp'),
    path('phone/verify-otp/', views.PhoneOTPVerifyView.as_view(), name='phone-verify-otp'),
    path('phone/login/', views.PhoneLoginView.as_view(), name='phone-login'),
    path('phone/verification-status/', views.phone_verification_status, name='phone-verification-status'),
    path('phone/resend-otp/', views.resend_phone_otp, name='resend-phone-otp'),
    
    # Email OTP authentication endpoints
    path('email/request-otp/', views.EmailOTPRequestView.as_view(), name='email-request-otp'),
    path('email/verify-otp/', views.EmailOTPVerifyView.as_view(), name='email-verify-otp'),
    path('email/login/', views.EmailLoginView.as_view(), name='email-login'),
    
    # Unified OTP authentication endpoints (recommended)
    path('otp/request/', views.UnifiedOTPRequestView.as_view(), name='unified-otp-request'),
    path('otp/verify/', views.UnifiedOTPVerifyView.as_view(), name='unified-otp-verify'),
    
    # User profile endpoints
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    
    # Password reset endpoints
    path('password-reset/', views.PasswordResetView.as_view(), name='password-reset'),
    path('password-reset-confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    
    # Session management endpoints
    path('sessions/', views.user_sessions, name='user-sessions'),
    path('sessions/<int:session_id>/revoke/', views.revoke_session, name='revoke-session'),
]
