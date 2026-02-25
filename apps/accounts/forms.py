"""
Forms for E-RECYCLO accounts app
All forms with validation and error handling
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import Account, VendorDetails, CollectorProfile, ClientProfile
from config.validators import validate_indian_phone


# ============================================
# REGISTRATION FORM
# ============================================

class RegistrationForm(forms.ModelForm):
    """
    Complete registration form for all user types
    Step 1 of registration process
    """
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
            'placeholder': 'Enter password',
            'id': 'password'
        }),
        help_text="Must be 8+ characters with uppercase, lowercase, number, and special character"
    )
    
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
            'placeholder': 'Confirm password',
            'id': 'password_confirm'
        }),
        label="Confirm Password"
    )
    
    USER_TYPE_CHOICES = [
        ('client', 'Client (I want to recycle E-waste)'),
        ('vendor', 'Vendor (I recycle the . E-waste )'),
        ('collector', 'Collector (I collect the E-waste)'),
    ]
    
    user_type = forms.ChoiceField(
        choices=USER_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'user-type-radio'
        }),
        label="I am a",
        initial='client'
    )
    
    class Meta:
        model = Account
        fields = ['first_name', 'last_name', 'username', 'email', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                'placeholder': 'First Name',
                'id': 'first_name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                'placeholder': 'Last Name',
                'id': 'last_name'
            }),
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                'placeholder': 'Username (lowercase, no spaces)',
                'id': 'username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                'placeholder': 'Email Address',
                'id': 'email'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                'placeholder': '10-digit mobile number',
                'id': 'phone_number',
                'maxlength': '10'
            }),
        }
    
    def clean_username(self):
        """Validate username"""
        username = self.cleaned_data.get('username', '').lower().strip()
        
        if not username:
            raise ValidationError("Username is required.")
        
        if len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long.")
        
        if len(username) > 30:
            raise ValidationError("Username must be less than 30 characters.")
        
        if not username.replace('_', '').replace('.', '').isalnum():
            raise ValidationError("Username can only contain letters, numbers, underscore, and dot.")
        
        if Account.objects.filter(username=username).exists():
            raise ValidationError("This username is already taken.")
        
        return username
    
    def clean_email(self):
        """Validate email"""
        email = self.cleaned_data.get('email', '').lower().strip()
        
        if not email:
            raise ValidationError("Email is required.")
        
        # Check for disposable email domains
        disposable_domains = [
            'tempmail.com', '10minutemail.com', 'guerrillamail.com',
            'mailinator.com', 'throwaway.email', 'temp-mail.org'
        ]
        
        domain = email.split('@')[-1].lower()
        if domain in disposable_domains:
            raise ValidationError("Please use a permanent email address.")
        
        if Account.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        
        return email
    
    def clean_phone_number(self):
        """Validate phone number"""
        phone = self.cleaned_data.get('phone_number', '')
        return validate_indian_phone(phone)
    
    def clean_password_confirm(self):
        """Validate password confirmation"""
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        
        if password and password_confirm:
            if password != password_confirm:
                raise ValidationError("Passwords don't match.")
        
        return password_confirm
    
    def clean(self):
        """Additional form-level validation"""
        cleaned_data = super().clean()
        return cleaned_data
    
    def save(self, commit=True):
        """Save user with proper role assignment"""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        
        # Set user type based on selection
        user_type = self.cleaned_data.get('user_type')
        if user_type == 'client':
            user.is_client = True
        elif user_type == 'vendor':
            user.is_vendor = True
        elif user_type == 'collector':
            user.is_collector = True
        
        # User starts inactive (activated after email verification)
        user.is_active = False
        
        if commit:
            user.save()
        
        return user


# ============================================
# VENDOR PROFILE FORM
# ============================================

class VendorProfileForm(forms.ModelForm):
    """
    Vendor profile completion form
    All fields are required for approval
    """
    
    class Meta:
        model = VendorDetails
        fields = [
            'company_name', 'business_address', 'contact_person',
            'alternate_phone', 'latitude', 'longitude',
            'profile_photo', 'business_license', 'gst_certificate',
            'ewaste_authorization', 'id_proof',
            'gstin_number', 'license_number', 'aadhaar_number', 'pan_number'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                'placeholder': 'Registered Company Name',
                'required': True
            }),
            'business_address': forms.Textarea(attrs={
                'class': 'w-full text-sm px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                'rows': 3,
                'placeholder': 'Complete Business Address with Pincode',
                'required': True,
                'style':'resize:none'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                'placeholder': 'Primary Contact Person Name',
                'required': True
            }),
            'alternate_phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                'placeholder': 'Alternate Phone Number (Optional)',
                'maxlength': '10'
            }),
            'latitude': forms.HiddenInput(attrs={
                'id': 'latitude'
            }),
            'longitude': forms.HiddenInput(attrs={
                'id': 'longitude'
            }),
            'gstin_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 font-mono',
                'maxlength': '15',
            }),
            'license_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 font-mono',
            }),
            'aadhaar_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 font-mono',
                'maxlength': '12',
            }),
            'pan_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 font-mono',
                'maxlength': '10',
            }),
        }
        labels = {
            'company_name': 'Company Name *',
            'business_address': 'Business Address *',
            'contact_person': 'Contact Person *',
            'alternate_phone': 'Alternate Phone',
            'profile_photo': 'Company/Person Photo',
            'business_license': 'Business License *',
            'gst_certificate': 'GST Certificate *',
            'ewaste_authorization': 'E-Waste Authorization *',
            'id_proof': 'ID Proof (Aadhaar/PAN) *',
        }
        help_texts = {
            'business_license': 'Upload business registration license (PDF/Image, max 5MB)',
            'gst_certificate': 'Upload GST registration certificate (PDF/Image, max 5MB)',
            'ewaste_authorization': 'Upload E-Waste authorization from CPCB (PDF/Image, max 5MB)',
            'id_proof': 'Upload Aadhaar or PAN card (PDF/Image, max 5MB)',
        }
    
    def clean_company_name(self):
        """Validate company name"""
        company_name = self.cleaned_data.get('company_name', '').strip()
        if len(company_name) < 3:
            raise ValidationError("Company name must be at least 3 characters long.")
        return company_name
    
    def clean_alternate_phone(self):
        """Validate alternate phone if provided"""
        phone = self.cleaned_data.get('alternate_phone', '')
        if phone:
            return validate_indian_phone(phone)
        return phone
    
    def clean(self):
        cleaned_data = super().clean()
        # Removed strict lat/lng validation to allow draft saves
        # Location will be validated by ProfileCompletion model instead
        return cleaned_data


# ============================================
# COLLECTOR PROFILE FORM
# ============================================

class CollectorProfileForm(forms.ModelForm):
    """
    Collector profile completion form
    All fields are required for approval
    """
    
    class Meta:
        model = CollectorProfile
        fields = [
            'date_of_birth', 'address', 'vehicle_type', 'vehicle_number',
            'latitude', 'longitude',
            'profile_photo', 'driving_license', 'aadhaar_card', 'vehicle_rc',
            'aadhaar_number', 'license_number', 'vehicle_rc_number'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                'type': 'date'
            }),
            'address': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-sm',
                'rows': 3,
                'placeholder': 'Complete Residential Address with Pincode',
                'required': True,
                'style':'resize:none'
            }),
            'vehicle_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 ',
                'required': True
            }),
            'vehicle_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                'placeholder': 'e.g., MH12AB1234',
                'required': True
            }),
            'latitude': forms.HiddenInput(attrs={
                'id': 'latitude'
            }),
            'longitude': forms.HiddenInput(attrs={
                'id': 'longitude'
            }),
            'aadhaar_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 font-mono',
                'placeholder': 'XXXX-XXXX-1234',
                'maxlength': '12',
            }),
            'license_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 font-mono',
                'placeholder': 'DL Number (e.g., MH0120200012345)'
            }),
            'vehicle_rc_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 font-mono',
                'placeholder': 'e.g., MH12AB1234'
            }),
        }
        labels = {
            'date_of_birth': 'Date of Birth *',
            'address': 'Residential Address *',
            'vehicle_type': 'Vehicle Type *',
            'vehicle_number': 'Vehicle Registration Number *',
            'profile_photo': 'Profile Photo *',
            'driving_license': 'Driving License *',
            'aadhaar_card': 'Aadhaar Card *',
            'vehicle_rc': 'Vehicle RC *',
        }
        help_texts = {
            'profile_photo': 'Upload your photo (JPG/PNG, max 5MB)',
            'driving_license': 'Upload valid driving license (PDF/Image, max 5MB)',
            'aadhaar_card': 'Upload Aadhaar card (PDF/Image, max 5MB)',
            'vehicle_rc': 'Upload vehicle registration certificate (PDF/Image, max 5MB)',
        }
    
    def clean_vehicle_number(self):
        """Validate vehicle number format (optional for draft)"""
        vehicle_number = self.cleaned_data.get('vehicle_number', '').upper().replace(' ', '')
        
        # Skip validation if empty (draft mode)
        if not vehicle_number:
            return vehicle_number
        
        # Indian vehicle number format: AA00AA0000
        import re
        if not re.match(r'^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$', vehicle_number):
            raise ValidationError("Invalid vehicle number format. Use format: MH12AB1234")
        
        return vehicle_number
    
    def clean_date_of_birth(self):
        """Validate age (must be 18+) - optional for draft"""
        from datetime import date
        dob = self.cleaned_data.get('date_of_birth')
        
        # Skip validation if empty (draft mode)
        if not dob:
            return dob
        
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
        if age < 18:
            raise ValidationError("You must be at least 18 years old to register as a collector.")
        
        if age > 70:
            raise ValidationError("Please contact support for age verification.")
        
        return dob
    
    def clean(self):
        """Allow saving without all fields for draft mode"""
        cleaned_data = super().clean()
        # Remove strict validation to allow draft saves
        # Admin will verify all fields are complete before approving
        return cleaned_data


# ============================================
# CLIENT PROFILE FORM (Optional)
# ============================================

class ClientProfileForm(forms.ModelForm):
    """
    Client profile form (all fields optional)
    """
    
    class Meta:
        model = ClientProfile
        fields = ['gender', 'date_of_birth', 'address', 'profile_photo']
        widgets = {
            'gender': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                'type': 'date'
            }),
            'address': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                'rows': 3,
                'placeholder': 'Your Address (Optional)'
            }),
        }