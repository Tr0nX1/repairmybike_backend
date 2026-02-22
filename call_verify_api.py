import os
import django
import json
import base64

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')
django.setup()

from django.conf import settings
from rest_framework.test import APIRequestFactory
from authentication.views import UnifiedOTPVerifyView

def call_otp_verify_api(identifier, code, method):
    factory = APIRequestFactory()
    view = UnifiedOTPVerifyView.as_view()
    
    data = {
        'identifier': identifier,
        'otp_code': code,
        'method': method
    }
    
    request = factory.post('/auth/otp/verify/', data, format='json')
    # Add META data so _persist_user_session works
    request.META['HTTP_USER_AGENT'] = 'Script-Test'
    request.META['REMOTE_ADDR'] = '127.0.0.1'
    
    response = view(request)
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Verification Successful!")
        session_token = response.data.get('session_token')
        if session_token:
            print("\n--- Decoded JWT Payload ---")
            parts = session_token.split('.')
            if len(parts) == 3:
                payload = parts[1] + '=' * (4 - len(parts[1]) % 4)
                decoded = base64.b64decode(payload).decode('utf-8')
                data = json.loads(decoded)
                print(json.dumps(data, indent=2))
        
        print("\n--- User Data from API Response ---")
        print(json.dumps(response.data.get('user', {}), indent=2))
    else:
        print(f"Response Data: {response.data}")

if __name__ == "__main__":
    call_otp_verify_api("+918901232357", "723583", "phone")
