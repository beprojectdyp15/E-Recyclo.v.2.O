# Migration for adding weight and size fields to PhotoPost
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('client', '0007_photopost_delivery_otp_photopost_pickup_otp_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='photopost',
            name='estimated_weight',
            field=models.CharField(
                max_length=20,
                blank=True,
                choices=[
                    ('light', 'Light (< 5 kg)'),
                    ('medium', 'Medium (5-20 kg)'),
                    ('heavy', 'Heavy (20-50 kg)'),
                    ('very_heavy', 'Very Heavy (> 50 kg)'),
                ],
                help_text='Approximate weight of the item'
            ),
        ),
        migrations.AddField(
            model_name='photopost',
            name='item_size',
            field=models.CharField(
                max_length=20,
                blank=True,
                choices=[
                    ('small', 'Small (fits in backpack)'),
                    ('medium', 'Medium (fits on bike)'),
                    ('large', 'Large (needs auto/van)'),
                    ('very_large', 'Very Large (needs tempo/truck)'),
                ],
                help_text='Approximate size of the item'
            ),
        ),
    ]