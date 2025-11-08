from django.core.management.base import BaseCommand
from decimal import Decimal

from subscriptions.models import Plan


class Command(BaseCommand):
    help = "Seed sample subscription plans"

    def handle(self, *args, **options):
        basic_monthly, created1 = Plan.objects.get_or_create(
            slug="basic-monthly",
            defaults={
                "name": "Basic Monthly",
                "description": "Essential maintenance tips and booking priority.",
                "benefits": {
                    "priority_booking": True,
                    "reminders": ["service_due", "insurance_renewal"],
                    "discounts": {"services": 5},
                },
                "services": [
                    "Free Pickup & Drop (1x)",
                    "Engine Oil Replacement",
                    "Chain Cleaning & Lubrication",
                    "Brake Pad Check & Adjustment",
                ],
                "price": Decimal("99.00"),
                "currency": "INR",
                "billing_period": "monthly",
                "included_visits": 0,
                "active": True,
            },
        )

        # Ensure annual plan is migrated to yearly
        premium_annual = Plan.objects.filter(slug="premium-annual").first()
        premium_yearly, created2 = Plan.objects.get_or_create(
            slug="premium-yearly",
            defaults={
                "name": "Premium Yearly",
                "description": "Comprehensive benefits with bigger discounts.",
                "benefits": {
                    "priority_booking": True,
                    "reminders": ["service_due", "insurance_renewal", "pollution_check"],
                    "discounts": {"services": 15, "spare_parts": 10},
                    "free_pickup": True,
                },
                "services": [
                    "Unlimited Pickup & Drop",
                    "Comprehensive Service Package",
                    "Priority Support",
                    "Free Wash (Quarterly)",
                ],
                "price": Decimal("999.00"),
                "currency": "INR",
                "billing_period": "yearly",
                "included_visits": 12,
                "active": True,
            },
        )
        if premium_annual and premium_annual.slug != "premium-yearly" and not Plan.objects.filter(slug="premium-yearly").exists():
            # Update existing record to align with new period naming
            premium_annual.slug = "premium-yearly"
            premium_annual.name = "Premium Yearly"
            premium_annual.billing_period = "yearly"
            premium_annual.included_visits = 12
            premium_annual.save()

        # Add a Quarterly plan with 3 visits included
        standard_quarterly, created3 = Plan.objects.get_or_create(
            slug="standard-quarterly",
            defaults={
                "name": "Standard Quarterly",
                "description": "Quarterly plan with 3 included service visits.",
                "benefits": {
                    "priority_booking": True,
                    "reminders": ["service_due"],
                    "discounts": {"services": 10},
                },
                "services": [
                    "Priority Booking",
                    "Three Included Service Visits",
                    "Basic Wash (Monthly)",
                ],
                "price": Decimal("299.00"),
                "currency": "INR",
                "billing_period": "quarterly",
                "included_visits": 3,
                "active": True,
            },
        )

        # Ensure services are populated for existing records (if they predate JSONField)
        if not created1 and (not isinstance(basic_monthly.services, list) or len(basic_monthly.services) == 0):
            basic_monthly.services = [
                "Free Pickup & Drop (1x)",
                "Engine Oil Replacement",
                "Chain Cleaning & Lubrication",
                "Brake Pad Check & Adjustment",
            ]
            basic_monthly.save()

        if not created2 and (not isinstance(premium_yearly.services, list) or len(premium_yearly.services) == 0):
            premium_yearly.services = [
                "Unlimited Pickup & Drop",
                "Comprehensive Service Package",
                "Priority Support",
                "Free Wash (Quarterly)",
            ]
            premium_yearly.save()

        if not created3 and (not isinstance(standard_quarterly.services, list) or len(standard_quarterly.services) == 0):
            standard_quarterly.services = [
                "Priority Booking",
                "Three Included Service Visits",
                "Basic Wash (Monthly)",
            ]
            standard_quarterly.save()

        self.stdout.write(self.style.SUCCESS("Seeded subscription plans:"))
        for plan, created in [
            (basic_monthly, created1),
            (premium_yearly, created2),
            (standard_quarterly, created3),
        ]:
            self.stdout.write(self.style.SUCCESS(
                f"- {plan.name} | period={plan.billing_period} | price={plan.price} {plan.currency} | visits={plan.included_visits} | created={bool(created)}"
            ))
            if isinstance(plan.services, list) and plan.services:
                self.stdout.write(self.style.SUCCESS("  services:"))
                for s in plan.services:
                    self.stdout.write(self.style.SUCCESS(f"    • {s}"))