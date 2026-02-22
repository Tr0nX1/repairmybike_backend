import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

def check_user(descope_id):
    try:
        user = User.objects.get(descope_user_id=descope_id)
        print(f"User Found: {user.username}")
        print(f"Email: {user.email}")
        print(f"Staff: {user.is_staff}")
        print(f"Superuser: {user.is_superuser}")
        print(f"Verified: {user.is_verified}")
    except User.DoesNotExist:
        print("User not found in Django DB.")

if __name__ == "__main__":
    check_user("U35qReEXYDHb4hycSwccinTsNQlK")
