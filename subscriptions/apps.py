import logging
import os
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class SubscriptionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "subscriptions"

    def ready(self):
        import subscriptions.signals  # noqa: F401

        # APScheduler was used previously, now migrated to Celery for production reliability.
        # run_scheduler = os.environ.get('RUN_SCHEDULER', 'false').lower() == 'true'
        run_scheduler = False
        
        if run_scheduler:
            self._start_renewal_scheduler()

    def _start_renewal_scheduler(self):
        """Start APScheduler to run renewal task every 6 hours."""
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
            from subscriptions.tasks import process_subscription_renewals

            scheduler = BackgroundScheduler()
            
            # Run every 6 hours (at :00 of 0, 6, 12, 18 hours)
            scheduler.add_job(
                process_subscription_renewals,
                trigger=CronTrigger(hour='0,6,12,18', minute='0'),
                id='subscription_renewal',
                name='Process Subscription Renewals',
                replace_existing=True,
            )

            scheduler.start()
            logger.info("✓ APScheduler started for subscription renewals (every 6h)")
        except Exception as e:
            logger.error(f"⚠ Failed to start APScheduler: {e}")