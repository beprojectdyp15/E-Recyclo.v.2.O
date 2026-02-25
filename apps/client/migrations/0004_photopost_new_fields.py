from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('client', '0003_photopost_eco_points_awarded_and_more'),
    ]

    operations = [
        # Only adding NEW fields - pickup_otp and delivery_otp already exist in DB
        migrations.AddField(
            model_name='photopost',
            name='condition_notes',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='photopost',
            name='price_breakdown',
            field=models.TextField(blank=True, default=''),
        ),
        # Update status choices to include all new statuses
        migrations.AlterField(
            model_name='photopost',
            name='status',
            field=models.CharField(
                max_length=20, db_index=True, default='pending',
                choices=[
                    ('pending',           'Pending Vendor Assignment'),
                    ('assigned',          'Assigned to Vendor'),
                    ('accepted',          'Accepted by Vendor'),
                    ('pickup_scheduled',  'Pickup Scheduled'),
                    ('in_transit',        'In Transit'),
                    ('collected',         'Delivered to Vendor'),
                    ('under_review',      'Offer Under Review'),
                    ('completed',         'Completed'),
                    ('rejected',          'Rejected'),
                    ('returned_to_client','Returned to Client'),
                ],
            ),
        ),
    ]