"""
Middleware for E-RECYCLO accounts app
Access control based on profile completion
"""

from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class ProfileCompletionMiddleware:
    """
    Restricts access to certain features based on profile completion and approval status
    
    Rules:
    - Clients: Full access immediately (no approval needed)
    - Vendors/Collectors: Limited access until admin approves profile
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Process request
        if request.user.is_authenticated:
            # Skip for clients, admins, and superusers
            if (request.user.is_client or 
                request.user.is_admin or 
                request.user.is_superuser or
                request.user.is_staff):
                return self.get_response(request)
            
            # Check vendors and collectors
            if request.user.is_vendor or request.user.is_collector:
                try:
                    profile_completion = request.user.profile_completion
                    
                    # Define restricted URL patterns
                    restricted_paths = [
                        '/vendor/accept/',
                        '/vendor/reject/',
                        '/vendor/reports/',
                        '/vendor/payment/',
                        '/collector/accept-pickup/',
                        '/collector/complete/',
                        '/collector/earnings/',
                        '/wallet/withdraw/',
                        '/payments/request-withdrawal/',
                    ]
                    
                    current_path = request.path
                    
                    # Check if accessing restricted URL
                    is_restricted = any(current_path.startswith(path) for path in restricted_paths)
                    
                    if is_restricted and not profile_completion.can_use_platform_fully():
                        # User trying to access restricted feature without approval
                        
                        if profile_completion.approval_status == 'incomplete':
                            messages.warning(
                                request,
                                'Please complete your profile to access this feature.'
                            )
                            if request.user.is_vendor:
                                return redirect('/accounts/complete-vendor-profile/?unapproved_redirect=true')
                            else:
                                return redirect('/accounts/complete-collector-profile/?unapproved_redirect=true')
                        
                        elif profile_completion.approval_status == 'pending':
                            messages.info(
                                request,
                                'Your profile is under admin review.'
                            )
                            if request.user.is_vendor:
                                return redirect('/accounts/complete-vendor-profile/?unapproved_redirect=true')
                            else:
                                return redirect('/accounts/complete-collector-profile/?unapproved_redirect=true')
                        
                        elif profile_completion.approval_status == 'rejected':
                            messages.error(
                                request,
                                f'Your profile was rejected. Reason: {profile_completion.admin_remarks or "Incomplete profile details"}. Please update your profile and resubmit.'
                            )
                            if request.user.is_vendor:
                                return redirect('/accounts/complete-vendor-profile/?unapproved_redirect=true')
                            else:
                                return redirect('/accounts/complete-collector-profile/?unapproved_redirect=true')
                
                except Exception as e:
                    # Don't break the request if something goes wrong
                    pass
        
        response = self.get_response(request)
        return response


class EmailVerificationMiddleware:
    """
    Ensures users verify their email before accessing the platform
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Allow access to auth pages and static files
        allowed_paths = [
            '/accounts/register/',
            '/accounts/login/',
            '/accounts/verify-email/',
            '/accounts/resend-otp/',
            '/accounts/logout/',
            '/static/',
            '/media/',
            '/admin/',
        ]
        
        # Check if user is authenticated but not verified
        if request.user.is_authenticated and not request.user.is_active:
            # Skip check for allowed paths
            if not any(request.path.startswith(path) for path in allowed_paths):
                messages.warning(
                    request,
                    'Please verify your email address to continue.'
                )
                return redirect('accounts:verify_email')
        
        response = self.get_response(request)
        return response