from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('staff', '0008_activitylog_activity_lo_action__4f011a_idx_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activitylog',
            name='action_type',
            field=models.CharField(
                choices=[
                    ('status_change', 'Status Change'),
                    ('stock_update', 'Stock Update'),
                    ('price_change', 'Price Change'),
                    ('part_added', 'Part Added to Job'),
                    ('part_removed', 'Part Removed from Job'),
                    ('part_approved', 'Part Approved'),
                    ('part_rejected', 'Part Rejected'),
                    ('staff_created', 'Staff Created'),
                    ('staff_deactivated', 'Staff Deactivated'),
                    ('payment_verified', 'Payment Verified'),
                    ('cash_collected', 'Cash Collected'),
                    ('cash_reconciled', 'Cash Reconciled'),
                    ('cash_session_opened', 'Cash Session Opened'),
                    ('cash_session_closed', 'Cash Session Closed'),
                    ('stock_deducted', 'Stock Deducted'),
                    ('stock_reversed', 'Stock Reversed'),
                    ('price_locked', 'Price Locked'),
                    ('booking_cancelled', 'Booking Cancelled'),
                    ('mechanic_assigned', 'Mechanic Assigned'),
                ],
                max_length=20,
            ),
        ),
    ]
