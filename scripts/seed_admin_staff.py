import os
import sys
from pathlib import Path
import django

# Setup Django settings
# Ensure project root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "repairmybike.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from authentication.models import StaffDirectory


def ensure_user(username, email, password, is_staff=False, is_superuser=False):
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "is_staff": is_staff,
            "is_superuser": is_superuser,
            "is_active": True,
        },
    )

    # Update fields to match desired state
    changed = False
    if user.email != email:
        user.email = email
        changed = True
    if user.is_staff != is_staff:
        user.is_staff = is_staff
        changed = True
    if user.is_superuser != is_superuser:
        user.is_superuser = is_superuser
        changed = True

    # Always set the provided password
    user.set_password(password)
    changed = True
    user.save()

    return user, created


def ensure_staff_directory(identifier, name="", employee_id="", role="", is_active=True):
    entry, created = StaffDirectory.objects.get_or_create(
        identifier=identifier,
        defaults={
            "name": name,
            "employee_id": employee_id,
            "role": role,
            "is_active": is_active,
        },
    )
    return entry, created


if __name__ == "__main__":
    with transaction.atomic():
        # Admin user: login with username "admin@repairmybike.in"
        admin_user, admin_created = ensure_user(
            username="admin@repairmybike.in",
            email="admin@repairmybike.in",
            password="admin",
            is_staff=True,
            is_superuser=True,
        )

        # Staff user: login with username "staff@repairmybike.in"
        staff_user, staff_created = ensure_user(
            username="staff@repairmybike.in",
            email="staff@repairmybike.in",
            password="staff@rmb123",
            is_staff=True,
            is_superuser=False,
        )

        # StaffDirectory entry to enable JIT staff OTP login via API
        staff_dir_entry, dir_created = ensure_staff_directory(
            identifier="staff@repairmybike.in",
            name="Staff User",
            employee_id="S001",
            role="Mechanic",
            is_active=True,
        )

    print(
        {
            "admin": {"id": admin_user.id, "created": admin_created},
            "staff": {"id": staff_user.id, "created": staff_created},
            "staff_directory": {"id": staff_dir_entry.id, "created": dir_created},
        }
    )