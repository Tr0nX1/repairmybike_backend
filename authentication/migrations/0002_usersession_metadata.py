from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersession',
            name='device_id',
            field=models.CharField(max_length=255, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='usersession',
            name='user_agent',
            field=models.CharField(max_length=500, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='usersession',
            name='ip_address',
            field=models.CharField(max_length=100, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='usersession',
            name='last_activity',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]