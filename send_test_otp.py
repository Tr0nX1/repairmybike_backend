import os
from descope import DescopeClient, DeliveryMethod
from decouple import config

def send_otp(phone_number):
    try:
        project_id = "P320Gzmd6mIOt2NOn7WbViy50YyA"
        client = DescopeClient(project_id=project_id)
        
        print(f"Sending OTP to {phone_number}...")
        resp = client.otp.sign_up_or_in(
            method=DeliveryMethod.SMS,
            login_id=phone_number
        )
        print("Response received:")
        print(resp)
        return resp
    except Exception as e:
        print(f"Error sending OTP: {e}")
        return None

if __name__ == "__main__":
    send_otp("+918901232357")
