import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')
django.setup()

from content.models import Policy

# Path to the policies directory
POLICIES_DIR = os.path.join(os.path.dirname(__file__), 'policies')

# Mapping of file names to (title, slug)
policy_mapping = {
    'terms_and_conditions.md': ('Terms & Conditions', 'terms-and-conditions'),
    'privacy_policy.md': ('Privacy Policy', 'privacy-policy'),
    'refund_cancellation_policy.md': ('Refund & Cancellation Policy', 'refund-and-cancellation-policy'),
    'shipping_delivery_policy.md': ('Shipping & Delivery Policy', 'shipping-and-delivery-policy'),
    'payment_policy.md': ('Payment Policy', 'payment-policy'),
    'service_policy.md': ('Service Policy', 'service-policy'),
}

def populate():
    print(f"Reading policies from: {POLICIES_DIR}")
    
    for filename, (title, slug) in policy_mapping.items():
        file_path = os.path.join(POLICIES_DIR, filename)
        
        if not os.path.exists(file_path):
            print(f"Warning: File not found {file_path}")
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        obj, created = Policy.objects.update_or_create(
            slug=slug,
            defaults={
                'title': title,
                'content': content,
                'is_active': True
            }
        )
        
        if created:
            print(f"✅ Created policy: {title} ({slug})")
        else:
            print(f"⏳ Updated policy: {title} ({slug})")

if __name__ == '__main__':
    populate()
    print("\nPolicy synchronization complete.")
