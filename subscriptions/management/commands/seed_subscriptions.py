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
                "price": Decimal("299.00"),
                "currency": "INR",
                "billing_period": "quarterly",
                "included_visits": 3,
                "active": True,
            },
        )

        self.stdout.write(self.style.SUCCESS("Seeded subscription plans:"))
        self.stdout.write(self.style.SUCCESS(f"  {basic_monthly.name} (created: {bool(created1)})"))
        self.stdout.write(self.style.SUCCESS(f"  {premium_yearly.name} (created: {bool(created2)})"))
        self.stdout.write(self.style.SUCCESS(f"  {standard_quarterly.name} (created: {bool(created3)})"))