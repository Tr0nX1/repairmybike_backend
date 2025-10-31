from django.core.management.base import BaseCommand
from django.utils import timezone
from authentication.models import PhoneOTP, EmailOTP, OTPAttempt


class Command(BaseCommand):
    help = 'Clean up expired OTP records and reset rate limiting'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        
        # Clean up expired phone OTPs
        expired_phone_otps = PhoneOTP.objects.filter(expires_at__lt=now)
        phone_count = expired_phone_otps.count()
        
        # Clean up expired email OTPs
        expired_email_otps = EmailOTP.objects.filter(expires_at__lt=now)
        email_count = expired_email_otps.count()
        
        # Reset rate limiting for old attempts (older than 24 hours)
        old_attempts = OTPAttempt.objects.filter(
            last_attempt__lt=now - timezone.timedelta(hours=24)
        )
        attempts_count = old_attempts.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {phone_count} expired phone OTPs, '
                    f'{email_count} expired email OTPs, and reset {attempts_count} rate limiting attempts'
                )
            )
        else:
            # Delete expired OTPs
            expired_phone_otps.delete()
            expired_email_otps.delete()
            
            # Reset rate limiting
            for attempt in old_attempts:
                attempt.attempts_count = 0
                attempt.is_blocked = False
                attempt.blocked_until = None
                attempt.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully cleaned up {phone_count} expired phone OTPs, '
                    f'{email_count} expired email OTPs, and reset {attempts_count} rate limiting attempts'
                )
            )
