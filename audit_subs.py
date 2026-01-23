import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')
django.setup()

from subscriptions.models import Subscription
from django.contrib.auth import get_user_model
User = get_user_model()

def audit_subscriptions():
    print("--- auditing subscriptions ---")
    total = Subscription.objects.count()
    unlinked = Subscription.objects.filter(user__isnull=True).count()
    linked = Subscription.objects.filter(user__isnull=False).count()
    
    print(f"Total Subscriptions: {total}")
    print(f"Linked to User: {linked}")
    print(f"Unlinked (Orphaned): {unlinked}")
    
    print("\n--- Fixing Unlinked Subscriptions ---")
    orphans = Subscription.objects.filter(user__isnull=True).exclude(contact_phone__isnull=True)
    
    count_fixed = 0
    for sub in orphans:
        phone = sub.contact_phone
        if not phone:
            continue
            
        # Normalize phone? Assuming checking exact match or with/without +
        # User 22 has +91... Sub 3 has +91...
        # Look for user with this phone
        
        # Note: We don't know the exact field name for phone on User model easily without inspecting,
        # but the previous output showed `getattr(u, 'phone_number', 'N/A')` returning values.
        # So 'phone_number' is likely the field or property.
        
        # But we need to Query it.
        # Try finding user by phone_number
        try:
           user = User.objects.get(phone_number=phone)
           sub.user = user
           sub.save()
           print(f"✅ Linked Subscription {sub.id} to User {user.id} ({user.phone_number})")
           count_fixed += 1
        except User.DoesNotExist:
            print(f"⚠️ No user found for phone {phone} (Sub {sub.id})")
        except User.MultipleObjectsReturned:
            print(f"⚠️ Multiple users found for phone {phone} (Sub {sub.id}) - skipping safety")
            
    print(f"\nFixed {count_fixed} subscriptions.")

if __name__ == "__main__":
    audit_subscriptions()
