# Generated migration for collector app

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
import django.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('client', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CollectorPickup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('assigned', 'Assigned'), ('accepted', 'Accepted by Collector'), ('in_progress', 'Pickup In Progress'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='assigned', max_length=20)),
                ('scheduled_date', models.DateTimeField(blank=True, null=True)),
                ('pickup_date', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('proof_photo', models.ImageField(blank=True, null=True, upload_to='collector/proof/%Y/%m/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])),
                ('notes', models.TextField(blank=True)),
                ('base_fee', models.DecimalField(decimal_places=2, default='50.00', max_digits=10)),
                ('distance_fee', models.DecimalField(decimal_places=2, default='0.00', max_digits=10)),
                ('total_payment', models.DecimalField(decimal_places=2, default='50.00', max_digits=10)),
                ('payment_status', models.CharField(choices=[('pending', 'Pending'), ('paid', 'Paid')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('collector', models.ForeignKey(limit_choices_to={'is_collector': True}, on_delete=django.db.models.deletion.CASCADE, related_name='collector_pickups', to=settings.AUTH_USER_MODEL)),
                ('photo_post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='collector_pickups', to='client.photopost')),
            ],
            options={
                'db_table': 'collector_collectorpickup',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CollectorEarnings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_pickups', models.IntegerField(default=0)),
                ('completed_pickups', models.IntegerField(default=0)),
                ('total_earned', models.DecimalField(decimal_places=2, default='0.00', max_digits=10)),
                ('total_withdrawn', models.DecimalField(decimal_places=2, default='0.00', max_digits=10)),
                ('available_balance', models.DecimalField(decimal_places=2, default='0.00', max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('collector', models.OneToOneField(limit_choices_to={'is_collector': True}, on_delete=django.db.models.deletion.CASCADE, related_name='collector_earnings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'collector_collectorearnings',
            },
        ),
    ]
