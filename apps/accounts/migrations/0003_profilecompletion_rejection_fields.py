# Generated migration for ProfileCompletion rejection fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_add_all_fields'),  # Update this to your latest migration
    ]

    operations = [
        migrations.AddField(
            model_name='profilecompletion',
            name='rejection_reason',
            field=models.TextField(blank=True, help_text='Reason for rejection (shown to vendor/collector)'),
        ),
        migrations.AddField(
            model_name='profilecompletion',
            name='rejected_at',
            field=models.DateTimeField(blank=True, help_text='When profile was rejected', null=True),
        ),
    ]