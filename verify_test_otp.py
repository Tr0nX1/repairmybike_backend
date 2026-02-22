import os
import json
from descope import DescopeClient, DeliveryMethod
from django.conf import settings

def verify_otp(phone_number, code):
    try:
        project_id = "P320Gzmd6mIOt2NOn7WbViy50YyA"
        client = DescopeClient(project_id=project_id)
        
        print(f"Verifying OTP for {phone_number}...")
        resp = client.otp.verify_code(
            method=DeliveryMethod.SMS,
            login_id=phone_number,
            code=code
        )
        print("\n--- Descope Verification Response ---")
        # Pretty print the response
        print(json.dumps(resp, indent=2))
        
        if 'sessionToken' in resp:
            print("\n--- Session JWT (Decoded header/payload parts) ---")
            jwt = resp['sessionToken']['jwt']
            parts = jwt.split('.')
            if len(parts) == 3:
                import base64
                payload = parts[1] + '=' * (4 - len(parts[1]) % 4)
                decoded = base64.b64decode(payload).decode('utf-8')
                data = json.loads(decoded)
                print("\n--- Decoded JWT Payload (Targeted Keys) ---")
                for key in ['roles', 'permissions', 'tenants', 'email', 'name', 'phone_number', 'sub']:
                    if key in data:
                        print(f"{key}: {data[key]}")
                    else:
                        print(f"{key}: Not found")
                # Also print the whole data just in case, but keys first
                # print(json.dumps(data, indent=2))
        
        return resp
    except Exception as e:
        print(f"Error verifying OTP: {e}")
        return None

if __name__ == "__main__":
    verify_otp("+918901232357", "590401")
