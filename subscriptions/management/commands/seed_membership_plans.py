from django.core.management.base import BaseCommand
from decimal import Decimal

from subscriptions.models import Plan


class Command(BaseCommand):
    help = "Seed Basic and Premium membership plans (quarterly, half-yearly, yearly) and deactivate others"

    def handle(self, *args, **options):
        # Deactivate all existing plans first so only memberships show in frontend
        Plan.objects.update(active=False)

        def mk_benefits(labour_discount: int):
            return {
                "priority_booking": labour_discount == 15,
                "discounts": {"labour": labour_discount},
                "reminders": ["service_due"],
                "notes": "Membership plan configured via seed script",
            }

        # BASIC
        basic_quarterly, c1 = Plan.objects.update_or_create(
            slug="basic-quarterly",
            defaults={
                "name": "Basic Plan",
                "description": "Basic membership with essential services",
                "benefits": mk_benefits(10),
                "price": Decimal("499.00"),
                "currency": "INR",
                "billing_period": "quarterly",
                "included_visits": 3,
                "active": True,
            },
        )

        basic_half, c2 = Plan.objects.update_or_create(
            slug="basic-half-yearly",
            defaults={
                "name": "Basic Plan",
                "description": "Basic membership with essential services",
                "benefits": mk_benefits(10),
                "price": Decimal("899.00"),
                "currency": "INR",
                "billing_period": "half_yearly",
                "included_visits": 3,
                "active": True,
            },
        )

        basic_yearly, c3 = Plan.objects.update_or_create(
            slug="basic-yearly",
            defaults={
                "name": "Basic Plan",
                "description": "Basic membership with essential services",
                "benefits": mk_benefits(10),
                "price": Decimal("1699.00"),
                "currency": "INR",
                "billing_period": "yearly",
                "included_visits": 6,
                "active": True,
            },
        )

        # PREMIUM
        premium_quarterly, c4 = Plan.objects.update_or_create(
            slug="premium-quarterly",
            defaults={
                "name": "Premium Plan",
                "description": "Premium membership with extended services",
                "benefits": mk_benefits(15),
                "price": Decimal("699.00"),
                "currency": "INR",
                "billing_period": "quarterly",
                "included_visits": 3,
                "active": True,
            },
        )

        premium_half, c5 = Plan.objects.update_or_create(
            slug="premium-half-yearly",
            defaults={
                "name": "Premium Plan",
                "description": "Premium membership with extended services",
                "benefits": mk_benefits(15),
                "price": Decimal("1299.00"),
                "currency": "INR",
                "billing_period": "half_yearly",
                "included_visits": 3,
                "active": True,
            },
        )

        premium_yearly, c6 = Plan.objects.update_or_create(
            slug="premium-yearly",
            defaults={
                "name": "Premium Plan",
                "description": "Premium membership with extended services",
                "benefits": mk_benefits(15),
                "price": Decimal("2499.00"),
                "currency": "INR",
                "billing_period": "yearly",
                "included_visits": 6,
                "active": True,
            },
        )

        self.stdout.write(self.style.SUCCESS("Seeded membership plans (active only):"))
        for p, c in [
            (basic_quarterly, c1),
            (basic_half, c2),
            (basic_yearly, c3),
            (premium_quarterly, c4),
            (premium_half, c5),
            (premium_yearly, c6),
        ]:
            self.stdout.write(self.style.SUCCESS(f"  {p.slug} - {p.price} ({'created' if c else 'updated'})"))