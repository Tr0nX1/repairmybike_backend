"""
Management command: python manage.py process_renewals

Processes subscription renewals and expirations.
Can be run manually or scheduled via cron / APScheduler.
"""
from django.core.management.base import BaseCommand
from subscriptions.tasks import process_subscription_renewals


class Command(BaseCommand):
    help = 'Process subscription auto-renewals and expire overdue subscriptions'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Processing subscription renewals...'))
        
        summary = process_subscription_renewals()
        
        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Renewal task completed:"
            f"\n  Renewed:  {summary['renewed']}"
            f"\n  Expired:  {summary['expired']}"
            f"\n  Reminders: {summary['reminders_sent']}"
            f"\n  Errors:   {len(summary['errors'])}"
        ))

        if summary['errors']:
            for err in summary['errors']:
                self.stdout.write(self.style.ERROR(
                    f"  ⚠ Subscription #{err['subscription_id']}: {err['error']}"
                ))
