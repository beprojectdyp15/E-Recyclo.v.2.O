from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        # Add latitude and longitude to CollectorProfile
        migrations.AddField(
            model_name='collectorprofile',
            name='latitude',
            field=models.FloatField(blank=True, help_text='Collector base location latitude', null=True),
        ),
        migrations.AddField(
            model_name='collectorprofile',
            name='longitude',
            field=models.FloatField(blank=True, help_text='Collector base location longitude', null=True),
        ),
        
        # VendorDetails document ID fields
        migrations.AddField(
            model_name='vendordetails',
            name='gstin_number',
            field=models.CharField(blank=True, help_text='15-digit GSTIN (e.g., 27AABCU9603R1ZM)', max_length=15),
        ),
        migrations.AddField(
            model_name='vendordetails',
            name='license_number',
            field=models.CharField(blank=True, help_text='Business License Number', max_length=50),
        ),
        migrations.AddField(
            model_name='vendordetails',
            name='aadhaar_number',
            field=models.CharField(blank=True, help_text='12-digit Aadhaar Number (masked for security)', max_length=12),
        ),
        migrations.AddField(
            model_name='vendordetails',
            name='pan_number',
            field=models.CharField(blank=True, help_text='10-character PAN Number (e.g., ABCDE1234F)', max_length=10),
        ),
        
        # CollectorProfile document ID fields
        migrations.AddField(
            model_name='collectorprofile',
            name='aadhaar_number',
            field=models.CharField(blank=True, help_text='12-digit Aadhaar Number (masked for security)', max_length=12),
        ),
        migrations.AddField(
            model_name='collectorprofile',
            name='license_number',
            field=models.CharField(blank=True, help_text='Driving License Number', max_length=20),
        ),
        migrations.AddField(
            model_name='collectorprofile',
            name='vehicle_rc_number',
            field=models.CharField(blank=True, help_text='Vehicle Registration Number', max_length=20),
        ),
    ]