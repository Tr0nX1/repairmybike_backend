from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserSession, PhoneOTP, EmailOTP, OTPAttempt

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone_number', 'profile_picture', 'is_verified',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserRegistrationSerializer(serializers.Serializer):
    """Serializer for user registration via Descope"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=30, required=False)
    last_name = serializers.CharField(max_length=30, required=False)
    phone_number = serializers.CharField(max_length=20, required=False)


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class PasswordResetSerializer(serializers.Serializer):
    """Serializer for password reset"""
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation"""
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)


class UserSessionSerializer(serializers.ModelSerializer):
    """Serializer for user sessions"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserSession
        fields = ['id', 'user', 'expires_at', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone_number', 'profile_picture'
        ]


class PhoneOTPRequestSerializer(serializers.Serializer):
    """Serializer for requesting phone OTP"""
    phone_number = serializers.CharField(max_length=20)
    
    def validate_phone_number(self, value):
        """Validate phone number format"""
        import re
        # Basic phone number validation (adjust regex as needed)
        phone_pattern = r'^\+?[1-9]\d{1,14}$'
        if not re.match(phone_pattern, value):
            raise serializers.ValidationError("Invalid phone number format")
        return value


class PhoneOTPVerifySerializer(serializers.Serializer):
    """Serializer for verifying phone OTP"""
    phone_number = serializers.CharField(max_length=20)
    otp_code = serializers.CharField(max_length=10, min_length=4)
    
    def validate_otp_code(self, value):
        """Validate OTP code format"""
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must contain only digits")
        return value


class PhoneLoginSerializer(serializers.Serializer):
    """Serializer for phone-based login"""
    phone_number = serializers.CharField(max_length=20)
    otp_code = serializers.CharField(max_length=10, min_length=4)
    
    def validate_phone_number(self, value):
        """Validate phone number format"""
        import re
        phone_pattern = r'^\+?[1-9]\d{1,14}$'
        if not re.match(phone_pattern, value):
            raise serializers.ValidationError("Invalid phone number format")
        return value
    
    def validate_otp_code(self, value):
        """Validate OTP code format"""
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must contain only digits")
        return value


class EmailOTPRequestSerializer(serializers.Serializer):
    """Serializer for requesting email OTP"""
    email = serializers.EmailField()
    
    def validate_email(self, value):
        """Validate email format"""
        return value.lower().strip()


class EmailOTPVerifySerializer(serializers.Serializer):
    """Serializer for verifying email OTP"""
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=10, min_length=4)
    
    def validate_email(self, value):
        """Validate email format"""
        return value.lower().strip()
    
    def validate_otp_code(self, value):
        """Validate OTP code format"""
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must contain only digits")
        return value


class EmailLoginSerializer(serializers.Serializer):
    """Serializer for email-based login"""
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=10, min_length=4)
    
    def validate_email(self, value):
        """Validate email format"""
        return value.lower().strip()
    
    def validate_otp_code(self, value):
        """Validate OTP code format"""
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must contain only digits")
        return value


class UnifiedOTPRequestSerializer(serializers.Serializer):
    """Serializer for unified OTP request (phone or email)"""
    identifier = serializers.CharField(max_length=255)
    method = serializers.ChoiceField(choices=[('phone', 'Phone'), ('email', 'Email')])
    
    def validate(self, data):
        identifier = data.get('identifier')
        method = data.get('method')
        
        if method == 'phone':
            import re
            phone_pattern = r'^\+?[1-9]\d{1,14}$'
            if not re.match(phone_pattern, identifier):
                raise serializers.ValidationError("Invalid phone number format")
        elif method == 'email':
            from django.core.validators import validate_email
            try:
                validate_email(identifier)
                data['identifier'] = identifier.lower().strip()
            except:
                raise serializers.ValidationError("Invalid email format")
        
        return data


class UnifiedOTPVerifySerializer(serializers.Serializer):
    """Serializer for unified OTP verification (phone or email)"""
    identifier = serializers.CharField(max_length=255)
    otp_code = serializers.CharField(max_length=10, min_length=4)
    method = serializers.ChoiceField(choices=[('phone', 'Phone'), ('email', 'Email')])
    
    def validate_otp_code(self, value):
        """Validate OTP code format"""
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must contain only digits")
        return value
    
    def validate(self, data):
        identifier = data.get('identifier')
        method = data.get('method')
        
        if method == 'phone':
            import re
            phone_pattern = r'^\+?[1-9]\d{1,14}$'
            if not re.match(phone_pattern, identifier):
                raise serializers.ValidationError("Invalid phone number format")
        elif method == 'email':
            from django.core.validators import validate_email
            try:
                validate_email(identifier)
                data['identifier'] = identifier.lower().strip()
            except:
                raise serializers.ValidationError("Invalid email format")
        
        return data