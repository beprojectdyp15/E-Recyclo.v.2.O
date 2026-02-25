import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('client', '0004_photopost_new_fields'),
    ]

    operations = [
        # New tracking fields on PhotoPost
        migrations.AddField(
            model_name='photopost',
            name='offer_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='photopost',
            name='rejection_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='photopost',
            name='vendor_declined_reevaluation',
            field=models.BooleanField(default=False),
        ),
        # Return flow fields
        migrations.AddField(
            model_name='photopost',
            name='return_collector',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='return_pickups',
                limit_choices_to={'is_collector': True},
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='photopost',
            name='return_pickup_otp',
            field=models.CharField(blank=True, default='', max_length=6),
        ),
        migrations.AddField(
            model_name='photopost',
            name='return_delivery_otp',
            field=models.CharField(blank=True, default='', max_length=6),
        ),
        # Update status choices with return flow + tag delivery
        migrations.AlterField(
            model_name='photopost',
            name='status',
            field=models.CharField(
                max_length=25, db_index=True, default='pending',
                choices=[
                    ('pending',                 'Pending Vendor Assignment'),
                    ('assigned',                'Assigned to Vendor'),
                    ('accepted',                'Accepted by Vendor'),
                    ('pickup_scheduled',        'Pickup Scheduled'),
                    ('in_transit',              'In Transit'),
                    ('collected',               'Delivered to Vendor'),
                    ('under_review',            'Offer Under Review'),
                    ('return_requested',        'Return Requested'),
                    ('return_pickup_scheduled', 'Return Pickup Scheduled'),
                    ('return_in_transit',       'Return In Transit'),
                    ('returned_to_client',      'Returned to Client'),
                    ('completed',               'Completed'),
                    ('rejected',                'Rejected'),
                ],
            ),
        ),
        # EvaluationHistory model
        migrations.CreateModel(
            name='EvaluationHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False)),
                ('evaluation_type', models.CharField(blank=True, max_length=20)),
                ('vendor_final_value', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('eco_points_awarded', models.IntegerField(default=0)),
                ('vendor_remarks', models.TextField(blank=True)),
                ('condition_notes', models.TextField(blank=True)),
                ('price_breakdown', models.TextField(blank=True)),
                ('evaluated_at', models.DateTimeField(auto_now_add=True)),
                ('rejected_by_client', models.BooleanField(default=False)),
                ('rejection_reason', models.TextField(blank=True)),
                ('post', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='evaluation_history',
                    to='client.photopost',
                )),
                ('vendor', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='evaluation_records',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'db_table': 'client_evaluationhistory', 'ordering': ['-evaluated_at']},
        ),
    ]