from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from authentication.models import UserSession, PhoneOTP, EmailOTP


class Command(BaseCommand):
    help = 'Deactivate expired sessions and remove stale OTP records'

    def handle(self, *args, **options):
        now = timezone.now()

        # Deactivate sessions past expiry
        expired = UserSession.objects.filter(is_active=True, expires_at__lt=now)
        count_expired = expired.update(is_active=False)
        self.stdout.write(self.style.SUCCESS(f'Deactivated {count_expired} expired sessions'))

        # Optional: prune very old inactive sessions (older than 30 days)
        cutoff = now - timedelta(days=30)
        pruned, _ = UserSession.objects.filter(is_active=False, created_at__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f'Pruned {pruned} old inactive session rows'))

        # Remove OTP entries older than 7 days
        otp_cutoff = now - timedelta(days=7)
        p_deleted, _ = PhoneOTP.objects.filter(created_at__lt=otp_cutoff).delete()
        e_deleted, _ = EmailOTP.objects.filter(created_at__lt=otp_cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {p_deleted + e_deleted} stale OTP rows'))