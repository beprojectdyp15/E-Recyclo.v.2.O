"""
Django admin configuration for accounts app
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    Account, EmailVerification, ProfileCompletion,
    ClientProfile, VendorDetails, CollectorProfile, AdminProfile
)


@admin.register(Account)
class AccountAdmin(BaseUserAdmin):
    """Custom admin for Account model"""
    
    class ClientProfileInline(admin.StackedInline):
        model = ClientProfile
        can_delete = False
        extra = 0
        fields = ('profile_photo', 'gender', 'date_of_birth', 'address')

    class VendorDetailsInline(admin.StackedInline):
        model = VendorDetails
        can_delete = False
        extra = 0
        fields = ('profile_photo', 'company_name', 'contact_person', 'is_verified')

    class CollectorProfileInline(admin.StackedInline):
        model = CollectorProfile
        can_delete = False
        extra = 0
        fields = ('profile_photo', 'vehicle_type', 'vehicle_number')

    class AdminProfileInline(admin.StackedInline):
        model = AdminProfile
        can_delete = False
        extra = 0
        fields = ('profile_photo',)

    inlines = [ClientProfileInline, VendorDetailsInline, CollectorProfileInline, AdminProfileInline]
    
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
        from decimal import Decimal
        
        # Track credits given
        credited_count = 0
        
        for profile in queryset:
            if profile.approval_status != 'approved':
                profile.approval_status = 'approved'
                profile.admin_reviewed = True
                profile.admin_reviewed_by = request.user
                profile.approved_at = timezone.now()
                profile.save()
                
                # Development logic: Give ₹3000 initial balance to vendors
                if profile.user.is_vendor:
                    try:
                        wallet = profile.user.wallet
                        # Only credit if balance is 0 or it's a new approval
                        if wallet.total_earned == 0:
                            wallet.credit(Decimal('3000.00'), "Initial development credit (free of cost)")
                            credited_count += 1
                    except Exception as e:
                        self.message_user(request, f"Error crediting wallet for {profile.user.email}: {str(e)}", level='ERROR')
        
        success_msg = f"{queryset.count()} profile(s) approved successfully."
        if credited_count > 0:
            success_msg += f" {credited_count} vendor(s) received initiation credit (₹3000)."
            
        self.message_user(request, success_msg)
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
                'alternate_phone', 'use_registration_details', 'latitude', 'longitude', 'profile_photo'
            )
        }),
        ('Documents (Files)', {
            'fields': (
                'gst_certificate', 'pan_card', 'aadhaar_card', 'ewaste_authorization'
            )
        }),
        ('Regulatory IDs', {
            'fields': (
                'gstin_number', 'pan_number', 'aadhaar_number',
                'ewaste_auth_type', 'ewaste_auth_id'
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

@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at']
    search_fields = ['user__email', 'user__username']
