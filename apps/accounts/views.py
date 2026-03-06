"""
Views for E-RECYCLO accounts app
Complete authentication and profile management
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
import base64
import uuid

from .models import Account, EmailVerification, ProfileCompletion
from .forms import (
    RegistrationForm, VendorProfileForm, CollectorProfileForm, ClientProfileForm
)
from apps.notifications.utils import send_verification_email, send_profile_approved_email
from datetime import timedelta
import random


# ============================================
# HOME VIEW
# ============================================

def home_view(request):
    """Landing page - redirects authenticated users to their dashboard"""
    if request.user.is_authenticated:
        if request.user.is_client:
            return redirect('client:dashboard')
        elif request.user.is_vendor:
            profile_completion = getattr(request.user, 'profile_completion', None)
            if profile_completion and profile_completion.approval_status not in ['approved', 'pending']:
                return redirect('accounts:complete_vendor_profile')
            return redirect('vendor:dashboard')
        elif request.user.is_collector:
            profile_completion = getattr(request.user, 'profile_completion', None)
            if profile_completion and profile_completion.approval_status not in ['approved', 'pending']:
                return redirect('accounts:complete_collector_profile')
            return redirect('collector:dashboard')
        elif request.user.is_admin or request.user.is_superuser:
            return redirect('admin:index')
        else:
            # User has no role (corrupted registration) - logout and ask to re-register
            from django.contrib.auth import logout as auth_logout
            auth_logout(request)
            messages.error(request, 'Your account has incomplete registration. Please register again.')
            return redirect('accounts:register')
    
    return render(request, 'home.html')


# ============================================
# REGISTRATION - STEP 1: Basic Info
# ============================================

def register_view(request):
    """
    Step 1 of registration: Collect basic user information
    Creates inactive user account
    """
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        
        # Auto-cleanup orphaned unverified accounts with same email
        # This allows re-registration if OTP verification was interrupted
        email_input = request.POST.get('email', '').strip().lower()
        if email_input:
            Account.objects.filter(email=email_input, is_active=False).delete()
        
        if form.is_valid():
            try:
                # Create user (INACTIVE until email verified)
                user = form.save()
                
                # CRITICAL: User must be inactive
                user.is_active = False
                user.save()
                
                # Send verification email
                from apps.notifications.utils import send_verification_email
                email_sent = send_verification_email(user)
                
                if email_sent:
                    # Store user ID in session for OTP verification
                    request.session['verify_user_id'] = user.id
                    
                    messages.success(
                        request,
                        f'Registration successful! We sent a verification code to {user.email}. Check your email (or console in development).'
                    )
                    return redirect('accounts:verify_email')
                else:
                    messages.error(
                        request,
                        'Registration successful but email could not be sent. Please contact support.'
                    )
            
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
        else:
            # Form has errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = RegistrationForm()
    
    context = {
        'form': form,
        'page_title': 'Register - E-RECYCLO'
    }
    return render(request, 'accounts/register.html', context)

# ============================================
# REGISTRATION - STEP 2: Email Verification
# ============================================

def verify_email_view(request):
    """
    Step 2 of registration: Verify email with OTP
    Activates user account upon successful verification
    """
    # Get user ID from session
    user_id = request.session.get('verify_user_id')
    
    if not user_id:
        messages.error(request, 'Invalid session. Please register again.')
        return redirect('accounts:register')
    
    try:
        user = Account.objects.get(id=user_id)
    except Account.DoesNotExist:
        messages.error(request, 'User not found. Please register again.')
        del request.session['verify_user_id']
        return redirect('accounts:register')
    
    # Get email verification object
    try:
        email_verification = user.email_verification
    except:
        messages.error(request, 'Verification record not found. Please contact support.')
        return redirect('accounts:register')
    
    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()
        
        if not entered_otp:
            messages.error(request, 'Please enter the OTP code.')
        elif len(entered_otp) != 6:
            messages.error(request, 'OTP must be 6 digits.')
        else:
            # Verify OTP
            success, message = email_verification.verify_otp(entered_otp)
            
            if success:
                messages.success(request, message)
                
                # Clear session
                del request.session['verify_user_id']
                
                # Auto-login user
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                # Redirect based on role
                if user.is_client:
                    messages.info(request, 'Welcome! You can start uploading e-waste.')
                    return redirect('client:dashboard')
                elif user.is_vendor:
                    messages.info(request, 'Please complete your business profile for approval.')
                    return redirect('accounts:complete_vendor_profile')
                elif user.is_collector:
                    messages.info(request, 'Please complete your profile for approval.')
                    return redirect('accounts:complete_collector_profile')
            else:
                messages.error(request, message)
    
    # Check if can resend
    can_resend, resend_message = email_verification.can_resend()
    
    context = {
        'user': user,
        'email': user.email,
        'can_resend': can_resend,
        'resend_message': resend_message,
        'page_title': 'Verify Email - E-RECYCLO'
    }
    return render(request, 'accounts/verify_email.html', context)


# ============================================
# RESEND OTP
# ============================================

def resend_otp_view(request):
    """
    Resend OTP to user's email
    Has 1-minute cooldown to prevent spam
    """
    user_id = request.session.get('verify_user_id')
    
    if not user_id:
        messages.error(request, 'Invalid session.')
        return redirect('accounts:register')
    
    try:
        user = Account.objects.get(id=user_id)
        email_verification = user.email_verification
    except:
        messages.error(request, 'User not found.')
        return redirect('accounts:register')
    
    # Check if can resend
    can_resend, message = email_verification.can_resend()
    
    if can_resend:
        # Send new OTP
        send_verification_email(user)
        email_verification.mark_resent()
        messages.success(request, 'OTP sent successfully! Check your email.')
    else:
        messages.warning(request, message)
    
    return redirect('accounts:verify_email')


# ============================================
# LOGIN
# ============================================

def login_view(request):
    """Login with username OR email"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        identifier = request.POST.get('email', '').strip()  # Can be email OR username
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me')
        
        if not identifier or not password:
            messages.error(request, 'Please enter email/username and password.')
        else:
            user = None
            
            # Try email first
            try:
                u = Account.objects.get(email=identifier.lower())
                user = authenticate(request, email=u.email, password=password)
            except Account.DoesNotExist:
                pass
            
            # Try username if email failed
            if user is None:
                try:
                    u = Account.objects.get(username=identifier.lower())
                    user = authenticate(request, email=u.email, password=password)
                except Account.DoesNotExist:
                    pass
            
            if user is not None:
                if not user.is_active:
                    messages.error(request, 'Please verify your email first.')
                    return redirect('accounts:login')
                
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                if not remember_me:
                    request.session.set_expiry(0)
                
                messages.success(request, f'Welcome back, {user.get_full_name()}!')
                
                if user.is_superuser or user.is_admin:
                    return redirect('admin_custom:dashboard')
                elif user.is_client:
                    return redirect('client:dashboard')
                elif user.is_vendor:
                    profile_completion = getattr(user, 'profile_completion', None)
                    if profile_completion and profile_completion.approval_status not in ['approved', 'pending']:
                        messages.info(request, 'Please complete your business profile for approval.')
                        return redirect('accounts:complete_vendor_profile')
                    return redirect('vendor:dashboard')
                elif user.is_collector:
                    profile_completion = getattr(user, 'profile_completion', None)
                    if profile_completion and profile_completion.approval_status not in ['approved', 'pending']:
                        messages.info(request, 'Please complete your profile for approval.')
                        return redirect('accounts:complete_collector_profile')
                    return redirect('collector:dashboard')
                else:
                    return redirect('home')
            else:
                messages.error(request, 'Invalid email/username or password.')
    
    return render(request, 'accounts/login.html', {'page_title': 'Login'})


# ============================================
# LOGOUT
# ============================================

@login_required
def logout_view(request):
    """Logout user and redirect to home"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


# ============================================
# VENDOR PROFILE COMPLETION
# ============================================

@login_required
def complete_vendor_profile(request):
    """
    Vendor profile completion form
    Required for admin approval
    """
    if not request.user.is_vendor:
        messages.error(request, 'Access denied. This page is for vendors only.')
        return redirect('home')
    
    vendor_profile = request.user.vendor_profile
    profile_completion = request.user.profile_completion

    # Block form submission if approved or pending (but ALLOW if rejected)
    if profile_completion.approval_status == 'approved' and request.method == 'POST':
        messages.warning(request, 'Your profile is already approved and cannot be changed.')
        return redirect('vendor:dashboard')
    
    if profile_completion.approval_status == 'pending' and request.method == 'POST':
        action = request.POST.get('action')
        if action != 'save_draft':
            messages.warning(request, 'Your profile is under review. Please wait for admin decision.')
            return redirect('vendor:dashboard')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        form = VendorProfileForm(request.POST, request.FILES, instance=vendor_profile)
        
        # If saving draft, temporarily bypass required fields
        if action == 'save_draft':
            for field in form.fields.values():
                field.required = False
        
        if form.is_valid():
            try:
                # Handle "Use Registration Details" logic
                use_reg = form.cleaned_data.get('use_registration_details')
                vendor = form.save(commit=False)
                
                if use_reg:
                    # Sync from Account basic info
                    vendor.contact_person = f"{request.user.first_name} {request.user.last_name}".strip()
                    vendor.alternate_phone = request.user.phone_number
                
                vendor.save()
                
                # Refresh and update completion
                vendor_profile.refresh_from_db()
                completion_percentage = profile_completion.calculate_completion()
                
                if action == 'submit' and completion_percentage == 100:
                    profile_completion.profile_submitted = True
                    profile_completion.approval_status = 'pending'
                    profile_completion.submitted_at = timezone.now()
                    profile_completion.save()
                    messages.success(request, '✓ Profile submitted for verification! We will review it shortly.')
                    return redirect('vendor:dashboard')
                else:
                    if action == 'save_draft':
                        messages.success(request, '✓ Progress saved as draft! Your data is secure.')
                    else:
                        messages.success(request, f'✓ Progress saved! {completion_percentage}% complete.')
                
                # Re-init form with fresh data
                form = VendorProfileForm(instance=vendor_profile)
                
            except Exception as e:
                messages.error(request, f'Error saving profile: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').capitalize()}: {error}")
    else:
        form = VendorProfileForm(instance=vendor_profile)
    
    context = {
        'form': form,
        'completion_percentage': profile_completion.calculate_completion(),
        'missing_fields': profile_completion.missing_fields,
        'page_title': 'Complete Vendor Profile - E-RECYCLO',
        'profile_completion': profile_completion,
        'reg_data': {
            'name': f"{request.user.first_name} {request.user.last_name}".strip(),
            'phone': request.user.phone_number
        }
    }
    return render(request, 'accounts/complete_vendor_profile.html', context)


# ============================================
# COLLECTOR PROFILE COMPLETION
# ============================================

@login_required
def complete_collector_profile(request):
    """
    Collector profile completion form
    Required for admin approval
    """
    if not request.user.is_collector:
        messages.error(request, 'Access denied. This page is for collectors only.')
        return redirect('home')
    
    collector_profile = request.user.collector_profile
    profile_completion = request.user.profile_completion

    # Block form submission if approved or pending (but ALLOW if rejected)
    if profile_completion.approval_status == 'approved' and request.method == 'POST':
        messages.warning(request, 'Your profile is already approved and cannot be changed.')
        return redirect('collector:dashboard')
    
    if profile_completion.approval_status == 'pending' and request.method == 'POST':
        action = request.POST.get('action')
        if action != 'save_draft':
            messages.warning(request, 'Your profile is under review. Please wait for admin decision.')
            return redirect('collector:dashboard')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        form = CollectorProfileForm(request.POST, request.FILES, instance=collector_profile)
        
        # If saving draft, temporarily bypass required fields
        if action == 'save_draft':
            for field in form.fields.values():
                field.required = False

        if form.is_valid():
            try:
                form.save()  # This saves to the database
                
                # Refresh to get updated data
                collector_profile.refresh_from_db()
                form = CollectorProfileForm(instance=collector_profile)
                
                # Update profile completion
                completion_percentage = profile_completion.calculate_completion()
                
                if action == 'submit' and completion_percentage == 100:
                    profile_completion.profile_submitted = True
                    profile_completion.approval_status = 'pending'
                    profile_completion.submitted_at = timezone.now()
                    
                    # Clear rejection data if resubmitting after rejection
                    if profile_completion.rejection_reason:
                        profile_completion.rejection_reason = ''
                        profile_completion.rejected_at = None
                    
                    profile_completion.save()
                    
                    messages.success(request, '✓ Profile resubmitted successfully! Admin will review it soon.')
                    return redirect('collector:dashboard')
                else:
                    if action == 'save_draft':
                        messages.success(request, '✓ Progress saved as draft! Your data is secure.')
                    else:
                        messages.success(request, f'✓ Progress saved! {completion_percentage}% complete. Files uploaded successfully!')
            except Exception as e:
                messages.error(request, f'Error saving profile: {str(e)}')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        # GET request - create form with existing data
        form = CollectorProfileForm(instance=collector_profile)
    
    context = {
        'form': form,
        'completion_percentage': profile_completion.calculate_completion(),
        'missing_fields': profile_completion.missing_fields,
        'page_title': 'Complete Collector Profile - E-RECYCLO',
        'profile_completion': profile_completion,  # Add this for rejection display
    }
    return render(request, 'accounts/complete_collector_profile.html', context)



# ============================================
# PROFILE VIEW
# ============================================

@login_required
def profile_view(request):
    """View user profile - redirects vendors/collectors to complete profile page"""
    user = request.user
    
    # Redirect vendors/collectors if profile is not fully vetted
    profile_completion = getattr(user, 'profile_completion', None)
    is_vetted = profile_completion and profile_completion.approval_status == 'approved'
    is_pending = profile_completion and profile_completion.approval_status == 'pending'

    if user.is_vendor:
        if not (is_vetted or is_pending):
            return redirect('accounts:complete_vendor_profile')
        if is_vetted:
            # Verified vendors see the corporate registry view
            return render(request, 'accounts/vendor_profile.html', {
                'user': user,
                'page_title': 'Vendor Profile Registry'
            })
    
    elif user.is_collector:
        if not (is_vetted or is_pending):
            return redirect('accounts:complete_collector_profile')
    
    # Standard profile view for others (Clients, Collectors, Pending Users)
    context = {
        'user': user,
        'page_title': 'My Profile - E-RECYCLO'
    }
    
    if user.is_client:
        context['client_profile'] = user.client_profile
    
    return render(request, 'accounts/profile.html', context)


# ============================================
# EDIT PROFILE
# ============================================

@login_required
def edit_profile_view(request):
    """Edit user profile"""
    user = request.user
    
    if request.method == 'POST':
        # Update basic info
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.phone_number = request.POST.get('phone_number', '').strip()
        
        try:
            user.save()
            
            # Update role-specific profile
            if user.is_client:
                form = ClientProfileForm(request.POST, request.FILES, instance=user.client_profile)
                if form.is_valid():
                    form.save()
            elif user.is_vendor:
                # Update Vendor details from POST data
                vendor = user.vendor_profile
                vendor.contact_person = request.POST.get('contact_person', vendor.contact_person)
                vendor.alternate_phone = request.POST.get('alternate_phone', vendor.alternate_phone)
                vendor.company_name = request.POST.get('company_name', vendor.company_name)
                vendor.business_address = request.POST.get('business_address', vendor.business_address)
                vendor.save()
            elif user.is_collector:
                # Update Collector details from POST data
                collector = user.collector_profile
                collector.vehicle_type = request.POST.get('vehicle_type', collector.vehicle_type)
                collector.vehicle_number = request.POST.get('vehicle_number', collector.vehicle_number)
                collector.address = request.POST.get('address', collector.address)
                collector.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
    
    context = {
        'user': user,
        'page_title': 'Edit Profile - E-RECYCLO'
    }
    
    if user.is_client:
        context['form'] = ClientProfileForm(instance=user.client_profile)
    
    return render(request, 'accounts/edit_profile.html', context)


# ============================================
# PASSWORD RESET (Placeholder for now)
# ============================================

def password_reset_view(request):
    """Password reset view (to be implemented)"""
    messages.info(request, 'Password reset feature coming soon!')
    return redirect('accounts:login')

# ============================================
# AJAX: USERNAME AVAILABILITY CHECK
# ============================================

@require_http_methods(["GET"])
def check_username_view(request):
    """
    Real-time username availability check (AJAX)
    Returns: { available: bool, suggestions: [str] }
    """
    username = request.GET.get('username', '').strip().lower()
    
    if len(username) < 3:
        return JsonResponse({'available': False, 'message': 'Username must be at least 3 characters', 'suggestions': []})
    
    if len(username) > 50:
        return JsonResponse({'available': False, 'message': 'Username too long', 'suggestions': []})
    
    import re
    if not re.match(r'^[a-z0-9._]+$', username):
        return JsonResponse({'available': False, 'message': 'Only lowercase letters, numbers, dots, underscores', 'suggestions': []})
    
    exists = Account.objects.filter(username=username).exists()
    
    suggestions = []
    if exists:
        import random, string
        base = username[:30]
        for _ in range(3):
            suffix = ''.join(random.choices(string.digits, k=3))
            candidate = f"{base}{suffix}"
            if not Account.objects.filter(username=candidate).exists():
                suggestions.append(candidate)
    
    return JsonResponse({
        'available': not exists,
        'message': 'Available!' if not exists else 'Username already taken',
        'suggestions': suggestions
    })


# ============================================
# CLEANUP: Delete orphaned unverified accounts
# ============================================

@require_http_methods(["POST"])
def cleanup_registration_view(request):
    """
    Allow restarting registration by cleaning up orphaned unverified accounts.
    Called when user wants to re-register with same email.
    """
    email = request.POST.get('email', '').strip().lower()
    
    if not email:
        return JsonResponse({'success': False, 'message': 'Email required'})
    
    try:
        user = Account.objects.get(email=email, is_active=False)
        user.delete()
        return JsonResponse({'success': True, 'message': 'Previous registration cleared. You can register again.'})
    except Account.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'No pending registration found for this email'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

# ============================================
# FORGOT PASSWORD - Step 1: Enter Email
# ============================================

def forgot_password_view(request):
    """Step 1: Enter email to receive reset OTP"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        
        if not email:
            messages.error(request, 'Please enter your email.')
        else:
            try:
                user = Account.objects.get(email=email, is_active=True)
                
                # Generate OTP
                otp = str(random.randint(100000, 999999))
                
                # Store in session
                request.session['reset_user_id'] = user.id
                request.session['reset_otp'] = otp
                request.session['reset_otp_time'] = timezone.now().isoformat()
                
                # Send OTP email
                from apps.notifications.utils import send_password_reset_email
                send_password_reset_email(user, otp)
                
                # In development (console fallback)
                print(f"\n{'='*50}")
                print(f"PASSWORD RESET OTP for {user.email}: {otp}")
                print(f"{'='*50}\n")
                
                messages.success(request, f'Reset OTP sent to {email}.')
                return redirect('accounts:verify_reset_otp')
                
            except Account.DoesNotExist:
                messages.error(request, 'No account found with this email.')
    
    return render(request, 'accounts/forgot_password.html', {'page_title': 'Forgot Password'})


# ============================================
# FORGOT PASSWORD - Step 2: Verify OTP
# ============================================

def verify_reset_otp_view(request):
    """Step 2: Verify OTP"""
    user_id = request.session.get('reset_user_id')
    stored_otp = request.session.get('reset_otp')
    otp_time = request.session.get('reset_otp_time')
    
    if not user_id or not stored_otp:
        messages.error(request, 'Invalid session. Please start over.')
        return redirect('accounts:forgot_password')
    
    # Check OTP expiry (10 minutes)
    try:
        from datetime import datetime
        otp_created = datetime.fromisoformat(otp_time)
        if timezone.now() > timezone.make_aware(otp_created) + timedelta(minutes=10):
            messages.error(request, 'OTP expired. Please request a new one.')
            return redirect('accounts:forgot_password')
    except:
        pass
    
    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()
        
        if entered_otp == stored_otp:
            request.session['reset_verified'] = True
            messages.success(request, 'OTP verified! Set your new password.')
            return redirect('accounts:reset_password')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
    
    try:
        user = Account.objects.get(id=user_id)
        email = user.email
    except:
        email = ''
    
    return render(request, 'accounts/verify_reset_otp.html', {'email': email, 'page_title': 'Verify OTP'})


# ============================================
# FORGOT PASSWORD - Step 3: Reset Password
# ============================================

def reset_password_view(request):
    """Step 3: Set new password"""
    user_id = request.session.get('reset_user_id')
    verified = request.session.get('reset_verified')
    
    if not user_id or not verified:
        messages.error(request, 'Please verify OTP first.')
        return redirect('accounts:forgot_password')
    
    try:
        user = Account.objects.get(id=user_id)
    except Account.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('accounts:forgot_password')
    
    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm_password', '')
        
        if not password:
            messages.error(request, 'Please enter a password.')
        elif password != confirm:
            messages.error(request, 'Passwords do not match.')
        else:
            try:
                validate_password(password, user)
                user.set_password(password)
                user.save()
                
                # Clear session
                for key in ['reset_user_id', 'reset_otp', 'reset_otp_time', 'reset_verified']:
                    request.session.pop(key, None)
                
                messages.success(request, 'Password reset successfully! Please login.')
                return redirect('accounts:login')
            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, error)
    return render(request, 'accounts/reset_password.html', {
        'page_title': 'Reset Password - E-RECYCLO'
    })


# ============================================
# AJAX: UPDATE PROFILE PHOTO
# ============================================

@login_required
@require_http_methods(["POST"])
def update_profile_photo(request):
    """
    Handle AJAX profile picture upload with cropping
    """
    image_data = request.POST.get('image')
    if not image_data:
        return JsonResponse({'success': False, 'message': 'No image data received'})
    
    try:
        # Detect and remove data:image/...;base64, header
        if 'base64,' in image_data:
            format, imgstr = image_data.split('base64,')
        else:
            imgstr = image_data
            
        ext = 'png' # Default extension
        data = ContentFile(base64.b64decode(imgstr), name=f'profile_{request.user.id}_{uuid.uuid4().hex[:8]}.{ext}')
        
        user = request.user
        profile_instance = None
        
        if user.is_client:
            profile_instance = user.client_profile
        elif user.is_vendor:
            profile_instance = user.vendor_profile
        elif user.is_collector:
            profile_instance = user.collector_profile
            
        if profile_instance:
            profile_instance.profile_photo = data
            profile_instance.save()
            return JsonResponse({
                'success': True, 
                'message': 'Profile photo updated!',
                'image_url': profile_instance.profile_photo.url
            })
        else:
            return JsonResponse({'success': False, 'message': 'Profile record not found'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


# ============================================
# CHANGE PASSWORD (AUTHENTICATED)
# ============================================

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_messages['password_incorrect'] = "Your old password is incorrect. Please enter correct Password."

@login_required
def change_password_view(request):
    """
    Allow authenticated users to change their password securely
    """
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # This ensures the user isn't unexpectedly logged out
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated! 🔒')
            return redirect('accounts:profile')
        else:
            # Display form errors as messages or in template
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = CustomPasswordChangeForm(request.user)
        
    return render(request, 'accounts/change_password.html', {
        'form': form,
        'page_title': 'Change Password - E-RECYCLO'
    })
