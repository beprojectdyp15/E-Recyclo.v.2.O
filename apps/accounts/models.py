"""
Account models for E-RECYCLO
Complete user management system with email verification and profile completion
"""

from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from datetime import timedelta
import random

from .managers import AccountManager


# ============================================
# ACCOUNT MODEL (Custom User)
# ============================================

class Account(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model using email as the unique identifier
    Supports 4 user types: Client, Vendor, Collector, Admin
    """
    
    # Basic Information
    email = models.EmailField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="User's email address (used for login)"
    )
    username = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique username"
    )
    first_name = models.CharField(
        max_length=50,
        help_text="User's first name"
    )
    last_name = models.CharField(
        max_length=50,
        help_text="User's last name"
    )
    phone_number = models.CharField(
        max_length=15,
        help_text="10-digit Indian mobile number"
    )
    
    # User Type Flags
    is_client = models.BooleanField(
        default=False,
        help_text="User is a client (uploads e-waste)"
    )
    is_vendor = models.BooleanField(
        default=False,
        help_text="User is a vendor (recycles e-waste)"
    )
    is_collector = models.BooleanField(
        default=False,
        help_text="User is a collector (picks up e-waste)"
    )
    
    # Django User Flags
    is_staff = models.BooleanField(
        default=False,
        help_text="User can access admin site"
    )
    is_active = models.BooleanField(
        default=False,
        help_text="User account is active (set to True after email verification)"
    )
    is_superuser = models.BooleanField(
        default=False,
        help_text="User has all permissions"
    )
    is_admin = models.BooleanField(
        default=False,
        help_text="User is an admin"
    )
    
    # Timestamps
    date_joined = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time when user registered"
    )
    last_login = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time of last login"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Date and time of last profile update"
    )
    
    # Custom manager
    objects = AccountManager()
    
    # Authentication settings
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        db_table = 'accounts_account'
        verbose_name = 'Account'
        verbose_name_plural = 'Accounts'
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['is_client', 'is_vendor', 'is_collector']),
        ]
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        """Return user's full name"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        """Return user's first name"""
        return self.first_name
    
    def get_role(self):
        """Return user's primary role"""
        if self.is_superuser or self.is_admin:
            return 'Admin'
        elif self.is_vendor:
            return 'Vendor'
        elif self.is_collector:
            return 'Collector'
        elif self.is_client:
            return 'Client'
        return 'Unknown'
    
    def has_perm(self, perm, obj=None):
        """Check if user has specific permission"""
        return self.is_superuser or self.is_admin
    
    def has_module_perms(self, app_label):
        """Check if user has permissions to view app"""
        return self.is_superuser or self.is_admin


# ============================================
# EMAIL VERIFICATION MODEL
# ============================================

class EmailVerification(models.Model):
    """
    Email verification system using OTP
    Auto-created when user registers
    """
    
    user = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name='email_verification',
        help_text="User associated with this verification"
    )
    
    # OTP Details
    otp_code = models.CharField(
        max_length=6,
        blank=True,
        help_text="6-digit OTP code"
    )
    otp_created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When OTP was generated"
    )
    otp_expires_at = models.DateTimeField(
        help_text="When OTP expires (10 minutes from creation)"
    )
    
    # Verification Status
    is_verified = models.BooleanField(
        default=False,
        help_text="Email has been verified"
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When email was verified"
    )
    
    # Attempt Tracking (prevent abuse)
    attempts = models.IntegerField(
        default=0,
        help_text="Number of OTP verification attempts"
    )
    max_attempts = models.IntegerField(
        default=5,
        help_text="Maximum allowed attempts"
    )
    last_attempt_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last verification attempt time"
    )
    
    # Resend Tracking
    resend_count = models.IntegerField(
        default=0,
        help_text="Number of times OTP was resent"
    )
    last_resend_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last OTP resend time"
    )
    
    class Meta:
        db_table = 'accounts_emailverification'
        verbose_name = 'Email Verification'
        verbose_name_plural = 'Email Verifications'
    
    def __str__(self):
        status = "Verified" if self.is_verified else "Pending"
        return f"{self.user.email} - {status}"
    
    def generate_otp(self):
        """Generate a new 6-digit OTP"""
        self.otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        self.otp_created_at = timezone.now()
        self.otp_expires_at = timezone.now() + timedelta(minutes=10)
        self.save(update_fields=['otp_code', 'otp_created_at', 'otp_expires_at'])
        return self.otp_code
    
    def is_otp_valid(self):
        """Check if OTP is still valid (not expired)"""
        if not self.otp_expires_at:
            return False
        return timezone.now() < self.otp_expires_at
    
    def verify_otp(self, entered_otp):
        """
        Verify entered OTP
        Returns: (success: bool, message: str)
        """
        # Update attempt tracking
        self.attempts += 1
        self.last_attempt_at = timezone.now()
        self.save(update_fields=['attempts', 'last_attempt_at'])
        
        # Check max attempts
        if self.attempts > self.max_attempts:
            return False, "Too many failed attempts. Please request a new OTP."
        
        # Check if OTP is expired
        if not self.is_otp_valid():
            return False, "OTP has expired. Please request a new one."
        
        # Verify OTP
        if self.otp_code == entered_otp:
            self.is_verified = True
            self.verified_at = timezone.now()
            self.user.is_active = True
            self.user.save(update_fields=['is_active'])
            self.save(update_fields=['is_verified', 'verified_at'])
            return True, "Email verified successfully!"
        else:
            remaining = self.max_attempts - self.attempts
            return False, f"Invalid OTP. {remaining} attempt(s) remaining."
    
    def can_resend(self):
        """
        Check if OTP can be resent
        Returns: (can_resend: bool, message: str)
        """
        if not self.last_resend_at:
            return True, ""
        
        time_since_last_resend = timezone.now() - self.last_resend_at
        cooldown_seconds = 60  # 1 minute cooldown
        
        if time_since_last_resend.total_seconds() < cooldown_seconds:
            wait_seconds = int(cooldown_seconds - time_since_last_resend.total_seconds())
            return False, f"Please wait {wait_seconds} seconds before resending."
        
        return True, ""
    
    def mark_resent(self):
        """Mark that OTP was resent"""
        self.resend_count += 1
        self.last_resend_at = timezone.now()
        self.save(update_fields=['resend_count', 'last_resend_at'])


# ============================================
# PROFILE COMPLETION MODEL
# ============================================

class ProfileCompletion(models.Model):
    """
    Tracks profile completion status for vendors and collectors
    Required for admin approval
    """
    
    user = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name='profile_completion',
        help_text="User associated with this profile completion tracker"
    )
    
    # Completion Tracking
    basic_info_complete = models.BooleanField(
        default=False,
        help_text="Basic information is complete"
    )
    documents_uploaded = models.BooleanField(
        default=False,
        help_text="Required documents are uploaded"
    )
    profile_submitted = models.BooleanField(
        default=False,
        help_text="Profile has been submitted for review"
    )
    
    # Progress
    completion_percentage = models.IntegerField(
        default=0,
        help_text="Profile completion percentage (0-100)"
    )
    missing_fields = models.JSONField(
        default=list,
        blank=True,
        help_text="List of missing required fields"
    )
    
    # Admin Review
    admin_reviewed = models.BooleanField(
        default=False,
        help_text="Admin has reviewed this profile"
    )
    admin_reviewed_by = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='profiles_reviewed',
        help_text="Admin who reviewed this profile"
    )
    
    # Approval Status
    APPROVAL_STATUS_CHOICES = [
        ('incomplete', 'Profile Incomplete'),
        ('pending', 'Pending Admin Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('resubmit', 'Needs Resubmission'),
    ]
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='incomplete',
        db_index=True,
        help_text="Current approval status"
    )
    
    admin_remarks = models.TextField(
        blank=True,
        help_text="Admin's remarks about the profile"
    )
    
    rejection_reason = models.TextField(
        blank=True,
        help_text="Reason for rejection (shown to vendor/collector)"
    )
    rejected_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When profile was rejected"
    )
    
    # Timestamps
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When profile was submitted for review"
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When profile was approved"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts_profilecompletion'
        verbose_name = 'Profile Completion'
        verbose_name_plural = 'Profile Completions'
        indexes = [
            models.Index(fields=['approval_status']),
            models.Index(fields=['profile_submitted']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.completion_percentage}% - {self.get_approval_status_display()}"
    
    def calculate_completion(self):
        """
        Calculate profile completion percentage
        Returns: int (0-100)
        """
        user = self.user
        
        # Clients don't need profile completion
        if user.is_client:
            return 100
        
        # Vendor completion
        elif user.is_vendor:
            try:
                vendor = user.vendor_profile
                required_fields = [
                    ('company_name', vendor.company_name),
                    ('business_address', vendor.business_address),
                    ('contact_person', vendor.contact_person),
                    ('latitude', vendor.latitude),
                    ('longitude', vendor.longitude),
                    ('business_license', vendor.business_license),
                    ('gst_certificate', vendor.gst_certificate),
                    ('ewaste_authorization', vendor.ewaste_authorization),
                    ('id_proof', vendor.id_proof),
                ]
                
                completed = sum(1 for _, value in required_fields if value)
                total = len(required_fields)
                percentage = int((completed / total) * 100)
                
                # Update missing fields
                missing = [name for name, value in required_fields if not value]
                self.missing_fields = missing
                self.completion_percentage = percentage
                self.save(update_fields=['completion_percentage', 'missing_fields'])
                
                return percentage
            except:
                return 0
        
        # Collector completion
        elif user.is_collector:
            try:
                collector = user.collector_profile
                required_fields = [
                    ('date_of_birth', collector.date_of_birth),
                    ('address', collector.address),
                    ('vehicle_type', collector.vehicle_type),
                    ('vehicle_number', collector.vehicle_number),
                    ('driving_license', collector.driving_license),
                    ('aadhaar_card', collector.aadhaar_card),
                    ('vehicle_rc', collector.vehicle_rc),
                    ('profile_photo', collector.profile_photo),
                ]
                
                completed = sum(1 for _, value in required_fields if value)
                total = len(required_fields)
                percentage = int((completed / total) * 100)
                
                # Update missing fields
                missing = [name for name, value in required_fields if not value]
                self.missing_fields = missing
                self.completion_percentage = percentage
                self.save(update_fields=['completion_percentage', 'missing_fields'])
                
                return percentage
            except:
                return 0
        
        return 0
    
    def can_use_platform_fully(self):
        """
        Check if user has full platform access
        Returns: bool
        """
        user = self.user
        
        # Clients have immediate access
        if user.is_client:
            return True
        
        # Vendors and collectors need approval
        if user.is_vendor or user.is_collector:
            return self.approval_status == 'approved'
        
        return False


# ============================================
# CLIENT PROFILE MODEL
# ============================================

class ClientProfile(models.Model):
    """
    Extended profile for clients
    Optional fields (not required for platform access)
    """
    
    user = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name='client_profile',
        help_text="Client user account"
    )
    
    # Personal Information (Optional)
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say'),
    ]
    gender = models.CharField(
        max_length=20,
        choices=GENDER_CHOICES,
        blank=True,
        help_text="Client's gender (optional)"
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        help_text="Date of birth (optional)"
    )
    
    # Address (Optional)
    address = models.TextField(
        blank=True,
        help_text="Complete address (optional)"
    )
    
    # Profile Photo (Optional)
    profile_photo = models.ImageField(
        upload_to='client_profiles/',
        default='client_profiles/default.png',
        blank=True,
        null=True,
        help_text="Profile photo (optional)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts_clientprofile'
        verbose_name = 'Client Profile'
        verbose_name_plural = 'Client Profiles'
    
    def __str__(self):
        return f"Client Profile - {self.user.email}"
    
    def get_completion_percentage(self):
        """Calculate optional profile completion"""
        fields = [self.gender, self.date_of_birth, self.address, self.profile_photo]
        completed = sum(1 for field in fields if field)
        return int((completed / 4) * 100)


# ============================================
# VENDOR DETAILS MODEL
# ============================================

class VendorDetails(models.Model):
    """
    Complete vendor profile with business information and documents
    All fields are REQUIRED for approval
    """
    
    user = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name='vendor_profile',
        help_text="Vendor user account"
    )
    
    # Business Information
    company_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Registered company name"
    )
    business_address = models.TextField(
        blank=True,
        help_text="Complete business address"
    )
    contact_person = models.CharField(
        max_length=100,
        blank=True,
        help_text="Primary contact person name"
    )
    alternate_phone = models.CharField(
        max_length=15,
        blank=True,
        help_text="Alternate contact number"
    )
    
    # Location (for distance calculation)
    latitude = models.FloatField(
        null=True,
        blank=True,
        help_text="Business location latitude"
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
        help_text="Business location longitude"
    )
    
    # Profile Photo
    profile_photo = models.ImageField(
        upload_to='vendor_profiles/',
        default='vendor_profiles/default.png',
        blank=True,
        null=True,
        help_text="Company/person photo"
    )
    
    # Required Documents
    business_license = models.FileField(
        upload_to='vendor/business_licenses/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        blank=True,
        null=True,
        help_text="Business registration license (PDF or image, max 5MB)"
    )
    gst_certificate = models.FileField(
        upload_to='vendor/gst_certificates/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        blank=True,
        null=True,
        help_text="GST registration certificate (PDF or image, max 5MB)"
    )
    ewaste_authorization = models.FileField(
        upload_to='vendor/ewaste_auth/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        blank=True,
        null=True,
        help_text="E-Waste Recycling Authorization from CPCB (PDF or image, max 5MB)"
    )
    id_proof = models.FileField(
        upload_to='vendor/id_proofs/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        blank=True,
        null=True,
        help_text="ID proof - Aadhaar/PAN/Driving License (PDF or image, max 5MB)"
    )
    
    # Document ID Numbers (Manual Entry)
    gstin_number = models.CharField(
        max_length=15,
        blank=True,
        help_text="15-digit GSTIN (e.g., 27AABCU9603R1ZM)"
    )
    license_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Business License Number"
    )
    aadhaar_number = models.CharField(
        max_length=12,
        blank=True,
        help_text="12-digit Aadhaar Number (masked for security)"
    )
    pan_number = models.CharField(
        max_length=10,
        blank=True,
        help_text="10-character PAN Number (e.g., ABCDE1234F)"
    )
    
    # Verification Status
    is_verified = models.BooleanField(
        default=False,
        help_text="Admin has verified this vendor"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts_vendordetails'
        verbose_name = 'Vendor Details'
        verbose_name_plural = 'Vendor Details'
    
    def __str__(self):
        return self.company_name or f"Vendor - {self.user.email}"
    
    def is_documents_complete(self):
        """Check if all required documents are uploaded"""
        return all([
            self.business_license,
            self.gst_certificate,
            self.ewaste_authorization,
            self.id_proof
        ])


# ============================================
# COLLECTOR PROFILE MODEL
# ============================================

class CollectorProfile(models.Model):
    """
    Complete collector profile with personal information and documents
    All fields are REQUIRED for approval
    """
    
    user = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name='collector_profile',
        help_text="Collector user account"
    )
    
    # Personal Information
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        help_text="Date of birth"
    )
    address = models.TextField(
        blank=True,
        help_text="Complete residential address"
    )
    
    # Vehicle Information
    VEHICLE_TYPE_CHOICES = [
        ('bike', 'Bike/Motorcycle'),
        ('scooter', 'Scooter'),
        ('auto', 'Auto Rickshaw'),
        ('van', 'Van/Small Truck'),
        ('tempo', 'Tempo'),
        ('pickup', 'Pickup Truck'),
    ]
    vehicle_type = models.CharField(
        max_length=20,
        choices=VEHICLE_TYPE_CHOICES,
        blank=True,
        help_text="Type of vehicle for collecting e-waste"
    )
    vehicle_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Vehicle registration number (e.g., MH12AB1234)"
    )
    
    # Profile Photo
    profile_photo = models.ImageField(
        upload_to='collector/profile_photos/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        help_text="Profile photo (JPG/PNG, max 5MB)"
    )
    
    # Required Documents
    driving_license = models.FileField(
        upload_to='collector/driving_licenses/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        blank=True,
        null=True,
        help_text="Valid driving license (PDF or image, max 5MB)"
    )
    aadhaar_card = models.FileField(
        upload_to='collector/aadhaar/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        blank=True,
        null=True,
        help_text="Aadhaar card copy (PDF or image, max 5MB)"
    )
    vehicle_rc = models.FileField(
        upload_to='collector/vehicle_rc/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])],
        blank=True,
        null=True,
        help_text="Vehicle Registration Certificate (PDF or image, max 5MB)"
    )
    
    # Location (for showing to vendors and routing)
    latitude = models.FloatField(
        null=True,
        blank=True,
        help_text="Collector base location latitude"
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
        help_text="Collector base location longitude"
    )
    
    # Document ID Numbers (Manual Entry)
    aadhaar_number = models.CharField(
        max_length=12,
        blank=True,
        help_text="12-digit Aadhaar Number (masked for security)"
    )
    license_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Driving License Number"
    )
    vehicle_rc_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Vehicle Registration Number"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts_collectorprofile'
        verbose_name = 'Collector Profile'
        verbose_name_plural = 'Collector Profiles'
        indexes = [
            models.Index(fields=['vehicle_type']),
        ]
    
    def __str__(self):
        return f"Collector Profile - {self.user.email}"
    
    def is_documents_complete(self):
        """Check if all required documents are uploaded"""
        return all([
            self.driving_license,
            self.aadhaar_card,
            self.vehicle_rc,
            self.profile_photo
        ])
    
    def get_vehicle_display_name(self):
        """Get formatted vehicle information"""
        if self.vehicle_type and self.vehicle_number:
            return f"{self.get_vehicle_type_display()} - {self.vehicle_number}"
        return "Vehicle not registered"