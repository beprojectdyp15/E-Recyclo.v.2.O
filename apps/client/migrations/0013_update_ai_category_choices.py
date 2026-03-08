"""
Django migration — updates PhotoPost.ai_category choices to match the
new 13-category system introduced by CategoryMapper v2.

Run:
    python manage.py makemigrations client --name update_ai_category_choices
    python manage.py migrate

Or copy this file to:
    apps/client/migrations/0013_update_ai_category_choices.py
"""

from django.db import migrations
import django.db.models


class Migration(migrations.Migration):

    dependencies = [
        # Change this to the latest migration in apps/client/migrations/
        ('client', '0012_evaluationhistory_client_requested_value'),
    ]

    operations = [
        migrations.AlterField(
            model_name='photopost',
            name='ai_category',
            field=django.db.models.CharField(
                blank=True,
                choices=[
                    ('smartphone',      'Smartphone & Mobile'),
                    ('laptop',          'Laptop & Notebook'),
                    ('computer',        'Desktop Computer'),
                    ('tablet',          'Tablet & E-Reader'),
                    ('monitor_tv',      'Monitor & Television'),
                    ('battery_charger', 'Battery & Charger'),
                    ('peripheral',      'Computer Peripheral'),
                    ('audio_visual',    'Audio & Camera'),
                    ('storage_network', 'Storage & Networking'),
                    ('gaming',          'Gaming Equipment'),
                    ('large_appliance', 'Large Appliance'),
                    ('small_appliance', 'Small Appliance'),
                    ('cable_component', 'Cable, Printer & Component'),
                    ('other',           'Other / Not E-Waste'),
                ],
                help_text='AI-detected category',
                max_length=50,
            ),
        ),
    ]