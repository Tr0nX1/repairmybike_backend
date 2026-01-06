import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'repairmybike.settings')
django.setup()

from subscriptions.models import Plan

def inject_demo_data():
    plans = [
        {
            "name": "Standard Membership",
            "slug": "standard-membership",
            "tier": "basic",
            "description": "Essential protection for your everyday commute. Covers basic maintenance and emergency help.",
            "price": 299.00,
            "billing_period": "monthly",
            "included_visits": 2,
            "services": ["Oil Change", "Brake Check", "General Wash"],
            "benefits": {
                "discount_parts": "5%",
                "roadside_assistance": "Free within 5km",
                "priority_booking": False
            }
        },
        {
            "name": "Elite Premium Protection",
            "slug": "elite-premium-protection",
            "tier": "premium",
            "description": "Comprehensive care for high-performance bikes. Full coverage for peace of mind.",
            "price": 999.00,
            "billing_period": "quarterly",
            "included_visits": 5,
            "services": ["Chain Polish", "Engine Tuning", "Deep Cleaning", "Battery Check"],
            "benefits": {
                "discount_parts": "15%",
                "roadside_assistance": "Unlimited",
                "priority_booking": True,
                "free_pick_drop": True
            }
        }
    ]

    for p in plans:
        obj, created = Plan.objects.update_or_create(
            slug=p['slug'],
            defaults=p
        )
        if created:
            print(f"Created plan: {obj.name}")
        else:
            print(f"Updated plan: {obj.name}")

if __name__ == "__main__":
    inject_demo_data()
