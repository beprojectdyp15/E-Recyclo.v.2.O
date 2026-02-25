"""
Django admin configuration for accounts app
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    Account, EmailVerification, ProfileCompletion,
    ClientProfile, VendorDetails, CollectorProfile
)


@admin.register(Account)
class AccountAdmin(BaseUserAdmin):
    """Custom admin for Account model"""
    
    list_display = [
        'email', 'username', 'first_name', 'last_name',
        'get_role', 'is_active', 'date_joined'
    ]
    list_filter = [
        'is_client', 'is_vendor', 'is_collector',
        'is_active', 'is_staff', 'date_joined'
    ]
    search_fields = ['email', 'username', 'first_name', 'last_name', 'phone_number']
    ordering = ['-date_joined']
    
    fieldsets = (
        ('Login Credentials', {
            'fields': ('email', 'password')
        }),
        ('Personal Information', {
            'fields': ('username', 'first_name', 'last_name', 'phone_number')
        }),
        ('User Type', {
            'fields': ('is_client', 'is_vendor', 'is_collector')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_admin')
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'username', 'first_name', 'last_name',
                'phone_number', 'password1', 'password2',
                'is_client', 'is_vendor', 'is_collector'
            )
        }),
    )
    
    readonly_fields = ['date_joined', 'last_login']


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    """Admin for EmailVerification"""
    
    list_display = [
        'user', 'is_verified', 'otp_code',
        'otp_expires_at', 'attempts', 'resend_count'
    ]
    list_filter = ['is_verified', 'otp_created_at']
    search_fields = ['user__email', 'user__username']
    readonly_fields = [
        'otp_created_at', 'otp_expires_at', 'verified_at',
        'attempts', 'last_attempt_at', 'resend_count', 'last_resend_at'
    ]
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('OTP Details', {
            'fields': ('otp_code', 'otp_created_at', 'otp_expires_at')
        }),
        ('Verification Status', {
            'fields': ('is_verified', 'verified_at')
        }),
        ('Attempt Tracking', {
            'fields': ('attempts', 'max_attempts', 'last_attempt_at')
        }),
        ('Resend Tracking', {
            'fields': ('resend_count', 'last_resend_at')
        }),
    )


@admin.register(ProfileCompletion)
class ProfileCompletionAdmin(admin.ModelAdmin):
    """Admin for ProfileCompletion"""
    
    list_display = [
        'user', 'completion_percentage', 'approval_status',
        'profile_submitted', 'admin_reviewed', 'submitted_at'
    ]
    list_filter = ['approval_status', 'admin_reviewed', 'profile_submitted']
    search_fields = ['user__email', 'user__username']
    actions = ['approve_profiles', 'reject_profiles']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Completion Status', {
            'fields': (
                'basic_info_complete', 'documents_uploaded',
                'profile_submitted', 'completion_percentage', 'missing_fields'
            )
        }),
        ('Admin Review', {
            'fields': (
                'approval_status', 'admin_reviewed', 'admin_reviewed_by',
                'admin_remarks', 'submitted_at', 'approved_at'
            )
        }),
    )
    
    readonly_fields = ['submitted_at', 'approved_at', 'created_at', 'updated_at']
    
    def approve_profiles(self, request, queryset):
        """Bulk approve profiles"""
        from django.utils import timezone
        queryset.update(
            approval_status='approved',
            admin_reviewed=True,
            admin_reviewed_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f"{queryset.count()} profile(s) approved successfully.")
    approve_profiles.short_description = "Approve selected profiles"
    
    def reject_profiles(self, request, queryset):
        """Bulk reject profiles"""
        queryset.update(
            approval_status='rejected',
            admin_reviewed=True,
            admin_reviewed_by=request.user
        )
        self.message_user(request, f"{queryset.count()} profile(s) rejected.")
    reject_profiles.short_description = "Reject selected profiles"


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    """Admin for ClientProfile"""
    
    list_display = ['user', 'gender', 'date_of_birth', 'created_at']
    search_fields = ['user__email', 'user__username']
    list_filter = ['gender', 'created_at']


@admin.register(VendorDetails)
class VendorDetailsAdmin(admin.ModelAdmin):
    """Admin for VendorDetails"""
    
    list_display = [
        'user', 'company_name', 'contact_person',
        'is_verified', 'created_at'
    ]
    list_filter = ['is_verified', 'created_at']
    search_fields = ['user__email', 'company_name', 'contact_person']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Business Information', {
            'fields': (
                'company_name', 'business_address', 'contact_person',
                'alternate_phone', 'latitude', 'longitude', 'profile_photo'
            )
        }),
        ('Documents', {
            'fields': (
                'business_license', 'gst_certificate',
                'ewaste_authorization', 'id_proof'
            )
        }),
        ('Verification', {
            'fields': ('is_verified',)
        }),
    )


@admin.register(CollectorProfile)
class CollectorProfileAdmin(admin.ModelAdmin):
    """Admin for CollectorProfile"""
    
    list_display = [
        'user', 'vehicle_type', 'vehicle_number',
        'date_of_birth', 'created_at'
    ]
    list_filter = ['vehicle_type', 'created_at']
    search_fields = ['user__email', 'vehicle_number']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Personal Information', {
            'fields': ('date_of_birth', 'address', 'profile_photo')
        }),
        ('Vehicle Information', {
            'fields': ('vehicle_type', 'vehicle_number')
        }),
        ('Documents', {
            'fields': ('driving_license', 'aadhaar_card', 'vehicle_rc')
        }),
    )