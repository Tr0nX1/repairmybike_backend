import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')
django.setup()

from content.models import Policy

policies = [
    {
        'title': 'Terms & Conditions',
        'slug': 'terms-and-conditions',
        'content': '# Terms & Conditions\n\nWelcome to RepairMyBike. By using our services, you agree to...\n\n## 1. Usage Rules\n...\n',
    },
    {
        'title': 'Privacy Policy',
        'slug': 'privacy-policy',
        'content': '# Privacy Policy\n\nWe value your privacy. We collect your phone number and location to...\n',
    },
    {
        'title': 'Refund & Cancellation Policy',
        'slug': 'refund-and-cancellation-policy',
        'content': '# Refund & Cancellation Policy\n\nService bookings can be cancelled up to 2 hours before the appointment...\n',
    },
    {
        'title': 'Shipping & Delivery Policy',
        'slug': 'shipping-and-delivery-policy',
        'content': '# Shipping & Delivery Policy\n\nSpare parts are typically delivered within 3-5 business days...\n',
    },
]

for p in policies:
    obj, created = Policy.objects.update_or_create(
        slug=p['slug'],
        defaults={'title': p['title'], 'content': p['content'], 'is_active': True}
    )
    if created:
        print(f"Created policy: {p['title']}")
    else:
        print(f"Updated policy: {p['title']}")
