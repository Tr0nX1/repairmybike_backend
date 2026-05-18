#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')
django.setup()

from django.contrib.auth import get_user_model
from vehicles.models import UserVehicle
from authentication.models import UserSession

User = get_user_model()

# First, check all users
print("All users in database (first 20):")
all_users = list(User.objects.values('id', 'username', 'phone_number', 'email', 'default_vehicle_id'))
for user in all_users[:20]:
    print(f"  ID={user['id']}, username={user['username']}, phone={user['phone_number']}, email={user['email']}, default_vehicle_id={user['default_vehicle_id']}")

print(f"\nTotal users: {User.objects.count()}")

# Now try to find the user
print("\n--- Searching for user 7495099124 ---")
try:
    u = User.objects.get(phone_number='7495099124')
    print(f"Found by phone '7495099124': ID={u.id}, username={u.username}")
except User.DoesNotExist:
    print("Not found by phone '7495099124'")

try:
    u = User.objects.get(phone_number='+917495099124')
    print(f"Found by phone '+917495099124': ID={u.id}, username={u.username}")
except User.DoesNotExist:
    print("Not found by phone '+917495099124'")

# Search with wildcard
matching = User.objects.filter(phone_number__icontains='7495099124')
if matching.exists():
    print(f"Found {matching.count()} user(s) containing '7495099124':")
    for u in matching:
        print(f"  ID={u.id}, phone={u.phone_number}, username={u.username}")
        print(f"  default_vehicle_id: {u.default_vehicle_id}")
        print()
        
        print("  UserVehicle rows (latest first):")
        uvs = list(UserVehicle.objects.filter(user=u).select_related('vehicle_model').values('id','vehicle_model_id','vehicle_model__name','is_default','created_at').order_by('-created_at'))
        for uv in uvs:
            print(f"    ID={uv['id']}, model_id={uv['vehicle_model_id']}, name={uv['vehicle_model__name']}, is_default={uv['is_default']}, created={uv['created_at']}")
        print()
        
        print("  UserSession rows (latest first):")
        sessions = list(UserSession.objects.filter(user=u).values('id','device_id','session_token','created_at','is_active').order_by('-created_at')[:20])
        for sess in sessions:
            token_preview = sess['session_token'][:30] if sess['session_token'] else 'None'
            print(f"    ID={sess['id']}, device_id={sess['device_id']}, token={token_preview}..., created={sess['created_at']}, active={sess['is_active']}")
else:
    print("No users containing '7495099124'")
