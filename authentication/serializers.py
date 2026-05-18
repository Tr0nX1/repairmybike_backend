from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserSession, PhoneOTP, EmailOTP, OTPAttempt, UserAddress, StaffDirectory, ContactSubmission
from vehicles.models import VehicleModel

User = get_user_model()


class StaffDirectorySerializer(serializers.ModelSerializer):
    class StaffDirectorySerializer(serializers.ModelSerializer):
        email = serializers.SerializerMethodField()
        photo_url = serializers.SerializerMethodField()
        is_manager = serializers.SerializerMethodField()

        class Meta:
            model = StaffDirectory
            fields = ['id', 'name', 'employee_id', 'role', 'is_active', 'email', 'photo', 'photo_url', 'is_manager', 'created_at']
            read_only_fields = ['id', 'created_at']

        def get_email(self, obj):
            identifier = (obj.identifier or '').strip()
            if '@' in identifier:
                return identifier
            return None

        def get_photo_url(self, obj):
            request = self.context.get('request')
            if obj.photo:
                return request.build_absolute_uri(obj.photo.url) if request else obj.photo.url
            return None

        def get_is_manager(self, obj):
            return str(obj.role).lower() in ['manager', 'admin', 'superuser']

    def get_is_manager(self, obj):
        return str(obj.role).lower() in ['manager', 'admin', 'superuser']


class CustomerCRMSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    phone_number = serializers.CharField(read_only=True)
    total_bookings = serializers.IntegerField(read_only=True)
    active_subscriptions = serializers.IntegerField(read_only=True)
    last_visit = serializers.DateField(read_only=True, required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'phone_number', 'email', 'total_ltv',
            'loyalty_points', 'referral_code', 'referred_by',
            'total_bookings', 'active_subscriptions', 'last_visit', 'created_at'
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class UserAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAddress
        fields = [
            'id', 'full_name', 'phone_number', 'flat_house_no',
            'area_street', 'landmark', 'pincode', 'town_city',
            'state', 'is_default', 'delivery_instructions', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class DefaultVehicleSerializer(serializers.ModelSerializer):
    """
    Returns a flat vehicle shape that Flutter's profile restore can parse.
    image is a plain URL string because Flutter calls .toString() on it.
    """
    brand_name = serializers.CharField(source='vehicle_brand.name', read_only=True)
    type_name = serializers.CharField(source='vehicle_brand.vehicle_type.name', read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = VehicleModel
        fields = ['id', 'name', 'brand_name', 'type_name', 'image']

    def get_image(self, obj):
        if not obj.image:
            return None
        try:
            url = obj.image.url
            request = self.context.get('request')
            return request.build_absolute_uri(url) if request else url
        except Exception:
            return None


class UserSerializer(serializers.ModelSerializer):
    addresses = UserAddressSerializer(many=True, read_only=True)
    profile_picture_url = serializers.SerializerMethodField()
    default_vehicle = DefaultVehicleSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone_number', 'profile_picture', 'profile_picture_url', 'is_verified',
            'is_manager', 'default_vehicle', 'addresses', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        if obj.profile_picture:
            return request.build_absolute_uri(obj.profile_picture.url) if request else obj.profile_picture.url
        return None


class UserRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=30, required=False)
    last_name = serializers.CharField(max_length=30, required=False)
    phone_number = serializers.CharField(max_length=20, required=False)


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class StaffOtpLoginSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=["sms", "email"])
    identifier = serializers.CharField()
    otp_code = serializers.CharField()
    device_id = serializers.CharField(required=False, allow_blank=True)


class StaffPasswordLoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)
    device_id = serializers.CharField(required=False, allow_blank=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)


class UserSessionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserSession
        fields = ['id', 'user', 'expires_at', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone_number', 'profile_picture', 'email'
        ]


class PhoneOTPRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    
    def validate_phone_number(self, value):
        import re
        phone_pattern = r'^\+?[1-9]\d{1,14}$'
        if not re.match(phone_pattern, value):
            raise serializers.ValidationError("Invalid phone number format")
        return value


class PhoneOTPVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    otp_code = serializers.CharField(max_length=10, min_length=4)
    
    def validate_otp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must contain only digits")
        return value


class PhoneLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    otp_code = serializers.CharField(max_length=10, min_length=4)
    
    def validate_phone_number(self, value):
        import re
        phone_pattern = r'^\+?[1-9]\d{1,14}$'
        if not re.match(phone_pattern, value):
            raise serializers.ValidationError("Invalid phone number format")
        return value
    
    def validate_otp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must contain only digits")
        return value


class EmailOTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        return value.lower().strip()


class EmailOTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=10, min_length=4)
    
    def validate_email(self, value):
        return value.lower().strip()
    
    def validate_otp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must contain only digits")
        return value


class EmailLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=10, min_length=4)
    
    def validate_email(self, value):
        return value.lower().strip()
    
    def validate_otp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must contain only digits")
        return value


class UnifiedOTPRequestSerializer(serializers.Serializer):
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
    identifier = serializers.CharField(max_length=255)
    otp_code = serializers.CharField(max_length=10, min_length=4)
    method = serializers.ChoiceField(choices=[('phone', 'Phone'), ('email', 'Email')])
    
    def validate_otp_code(self, value):
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


class ContactSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactSubmission
        fields = '__all__'
        read_only_fields = ['id', 'status', 'created_at']


class CustomerDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()
    vehicles = serializers.SerializerMethodField()
    addresses = UserAddressSerializer(many=True, read_only=True)
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    booking_count = serializers.IntegerField(source='total_bookings', read_only=True)
    recent_bookings = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'username', 'email', 'phone_number', 
            'profile_picture', 'profile_picture_url', 'created_at',
            'loyalty_points', 'total_ltv', 'referral_code', 
            'total_spent', 'booking_count', 'vehicles', 'addresses', 'recent_bookings'
        ]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        if obj.profile_picture:
            return request.build_absolute_uri(obj.profile_picture.url) if request else obj.profile_picture.url
        return None

    def get_vehicles(self, obj):
        from vehicles.serializers import UserVehicleSerializer
        return UserVehicleSerializer(obj.vehicles.all(), many=True, context=self.context).data

    def get_recent_bookings(self, obj):
        from bookings.models import Booking
        from bookings.serializers import BookingListSerializer
        bookings = Booking.objects.filter(customer__phone=obj.phone_number).order_by('-created_at')[:5]
        return BookingListSerializer(bookings, many=True, context=self.context).data
