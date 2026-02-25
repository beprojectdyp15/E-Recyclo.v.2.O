"""
Django signals for automatic object creation
Auto-creates related objects when user registers
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import Account, EmailVerification, ProfileCompletion, ClientProfile, VendorDetails, CollectorProfile


@receiver(post_save, sender=Account)
def create_user_related_objects(sender, instance, created, **kwargs):
    """
    Auto-create related objects when a new user is created
    
    Creates:
    - EmailVerification (with OTP generated)
    - ProfileCompletion
    - Wallet (imported from payments app)
    - AppreciationPoints (imported from client app)
    - Role-specific profiles (Client/Vendor/Collector)
    """
    if created:
        # 1. Create EmailVerification with OTP - FIXED VERSION
        # We need to set otp_expires_at manually because it's NOT NULL
        email_verification = EmailVerification(
            user=instance,
            otp_code='',  # Will be set by generate_otp()
            otp_expires_at=timezone.now() + timedelta(minutes=10)  # Set initial value
        )
        email_verification.save()
        # Now generate the actual OTP
        email_verification.generate_otp()
        
        # 2. Create ProfileCompletion
        ProfileCompletion.objects.create(user=instance)
        
        # 3. Create Wallet (import here to avoid circular imports)
        try:
            from apps.payments.models import Wallet
            Wallet.objects.create(user=instance)
        except Exception as e:
            print(f"Warning: Could not create wallet for {instance.email}: {e}")
        
        # 4. Create AppreciationPoints (import here to avoid circular imports)
        try:
            from apps.client.models import AppreciationPoints
            AppreciationPoints.objects.create(user=instance)
        except Exception as e:
            print(f"Warning: Could not create appreciation points for {instance.email}: {e}")
        
        # 5. Create role-specific profiles
        if instance.is_client:
            ClientProfile.objects.create(user=instance)
        
        if instance.is_vendor:
            VendorDetails.objects.create(user=instance)
        
        if instance.is_collector:
            CollectorProfile.objects.create(user=instance)