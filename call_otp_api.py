import os
import django

# Setup Django environment before importing models/views
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')
django.setup()

from django.conf import settings
from rest_framework.test import APIRequestFactory
from authentication.views import UnifiedOTPRequestView

def call_otp_request_api(identifier, method):
    factory = APIRequestFactory()
    view = UnifiedOTPRequestView.as_view()
    
    data = {
        'identifier': identifier,
        'method': method
    }
    
    request = factory.post('/auth/otp/request/', data, format='json')
    response = view(request)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Data: {response.data}")

if __name__ == "__main__":
    # Use the phone number provided by the user
    call_otp_request_api("+918901232357", "phone")
