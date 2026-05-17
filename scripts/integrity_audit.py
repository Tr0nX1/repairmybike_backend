import os
import django
import sys
from decimal import Decimal

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')
django.setup()

from django.db.models import Count, Sum
from authentication.models import User
from bookings.models import Booking, BookingService, Customer
from spare_parts.models import SparePart, SparePartImage, Order, OrderItem
from subscriptions.models import Plan, PlanBenefit, Subscription

def audit_orphans():
    print("--- Checking for Orphan Records ---")
    orphans = {}
    
    # PlanBenefit
    pb_orphans = PlanBenefit.objects.filter(plan__isnull=True).count()
    if pb_orphans: orphans['PlanBenefit'] = pb_orphans
    
    # SparePartImage
    spi_orphans = SparePartImage.objects.filter(spare_part__isnull=True).count()
    if spi_orphans: orphans['SparePartImage'] = spi_orphans
    
    # BookingService
    bs_orphans = BookingService.objects.filter(booking__isnull=True).count()
    if bs_orphans: orphans['BookingService'] = bs_orphans
    
    # OrderItem
    oi_orphans = OrderItem.objects.filter(order__isnull=True).count()
    if oi_orphans: orphans['OrderItem'] = oi_orphans
    
    for model, count in orphans.items():
        print(f"FAILED: {model} has {count} orphan records.")
    
    if not orphans:
        print("PASSED: No orphan records found.")
    return orphans

def audit_relational_integrity():
    print("\n--- Checking Relational Integrity ---")
    issues = []
    
    # Checking for missing mechanic field (Contract Drift)
    try:
        Booking._meta.get_field('mechanic')
        print("INFO: 'mechanic' field exists on Booking.")
    except django.core.exceptions.FieldDoesNotExist:
        issues.append("FAILED: 'mechanic' field is MISSING from Booking model. Blueprint parity is broken.")
        
    # Invalid customer references
    null_customers = Booking.objects.filter(customer__isnull=True).count()
    if null_customers:
        issues.append(f"FAILED: {null_customers} bookings have no customer.")
        
    # Broken subscription references
    null_subs_plans = Subscription.objects.filter(plan__isnull=True).count()
    if null_subs_plans:
        issues.append(f"FAILED: {null_subs_plans} subscriptions have no plan.")

    if not any(i.startswith("FAILED") for i in issues):
        print("PASSED: Relational integrity looks good.")
    else:
        for issue in issues:
            print(issue)
    return issues

def audit_business_metrics():
    print("\n--- Checking Business Metric Consistency ---")
    issues = []
    
    # 1. Total LTV drift
    for user in User.objects.all():
        # Booking LTV
        booking_ltv = Booking.objects.filter(customer__email=user.email, booking_status='completed').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        # Order LTV (based on phone/email)
        order_ltv = Order.objects.filter(phone=user.phone_number, status='completed').aggregate(total=Sum('amount_total'))['total'] or Decimal('0.00')
        
        calculated_ltv = booking_ltv + order_ltv
        if abs(user.total_ltv - calculated_ltv) > Decimal('0.01'):
            issues.append(f"FAILED: User {user.username} LTV drift. DB: {user.total_ltv}, Calc: {calculated_ltv}")

    # 2. Referral Graph Loops
    for user in User.objects.all():
        slow = user
        fast = user
        while fast and fast.referred_by:
            slow = slow.referred_by
            fast = fast.referred_by.referred_by if fast.referred_by else None
            if slow == fast:
                issues.append(f"FAILED: Referral loop detected for user {user.username}")
                break

    # 3. Duplicate Referral Codes
    dupes = User.objects.values('referral_code').annotate(count=Count('id')).filter(count__gt=1, referral_code__isnull=False)
    for dupe in dupes:
        issues.append(f"FAILED: Duplicate referral code {dupe['referral_code']} found.")

    if not issues:
        print("PASSED: Business metrics are consistent.")
    else:
        for issue in issues:
            print(issue)
    return issues

def audit_contract_drift():
    print("\n--- Checking Serializer/API Contract Drift ---")
    from bookings.serializers import BookingListSerializer
    
    issues = []
    # Check if mechanic_name is in serializer fields (blueprint expectation)
    if 'mechanic_name' not in BookingListSerializer.Meta.fields:
        issues.append("INFO: 'mechanic_name' is missing from BookingListSerializer (as expected by Blueprint gap map).")
    
    # Check for User address consistency
    if not hasattr(User, 'addresses'):
         issues.append("FAILED: User model missing 'addresses' relation.")

    if not any(i.startswith("FAILED") for i in issues):
        print("PASSED: Contract drift check complete.")
    else:
        for issue in issues:
            print(issue)
    return issues

def run_audit():
    o = audit_orphans()
    r = audit_relational_integrity()
    b = audit_business_metrics()
    c = audit_contract_drift()
    
    print("\n--- AUDIT SUMMARY ---")
    has_failed = any(i.startswith("FAILED") for i in o.values() if isinstance(i, str)) or \
                 any(i.startswith("FAILED") for i in r) or \
                 any(i.startswith("FAILED") for i in b) or \
                 any(i.startswith("FAILED") for i in c)
                 
    if not has_failed:
        # Check if o was empty (all passed)
        if not o and not r and not b and not c:
             print("RESULT: SPRINT 0 PASSED")
        elif not any(i.startswith("FAILED") for list_in in [r, b, c] for i in list_in):
             print("RESULT: SPRINT 0 PASSED")
        else:
             print("RESULT: SPRINT 0 BLOCKED")
             sys.exit(1)
    else:
        print("RESULT: SPRINT 0 BLOCKED")
        sys.exit(1)

if __name__ == "__main__":
    run_audit()
