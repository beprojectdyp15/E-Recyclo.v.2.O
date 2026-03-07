"""
Forms for E-RECYCLO accounts app
All forms with validation and error handling
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import Account, VendorDetails, CollectorProfile, ClientProfile, AdminProfile
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
            'class': 'w-full px-4 py-2 border border-gray-300 bg-white rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
            'placeholder': 'Enter password',
            'id': 'password'
        }),
        help_text="Must be 8+ characters with uppercase, lowercase, number, and special character"
    )
    
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 bg-white rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
            'placeholder': 'Confirm password',
            'id': 'password_confirm'
        }),
        label="Confirm Password"
    )
    
    USER_TYPE_CHOICES = [
        ('client', 'Client'),
        ('vendor', 'Vendor'),
        ('collector', 'Collector'),
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
                'class': 'w-full px-4 py-2 border border-gray-300 bg-white rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                'placeholder': 'First Name',
                'id': 'first_name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 bg-white rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                'placeholder': 'Last Name',
                'id': 'last_name'
            }),
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 bg-white rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                'placeholder': 'Username (lowercase, no spaces)',
                'id': 'username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 bg-white rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                'placeholder': 'Email Address',
                'id': 'email'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 bg-white rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
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
    
    def clean_password(self):
        """Validate password strength"""
        password = self.cleaned_data.get('password')
        if password:
            validate_password(password)
        return password
    
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
            'alternate_phone', 'date_of_birth', 'use_registration_details', 'latitude', 'longitude',
            'profile_photo', 'gst_certificate', 'gstin_number', 
            'pan_card', 'pan_number', 'aadhaar_card', 'aadhaar_number',
            'ewaste_auth_type', 'ewaste_authorization', 'ewaste_auth_id'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                'type': 'date'
            }),
            'use_registration_details': forms.CheckboxInput(attrs={
                'class': 'rounded text-primary focus:ring-primary h-5 w-5',
                'id': 'use_reg_details'
            }),
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
            'gst_certificate': 'GST Certificate *',
            'pan_card': 'PAN Card *',
            'aadhaar_card': 'Aadhaar Card *',
            'ewaste_authorization': 'E-Waste Authorization *',
        }
        help_texts = {
            'gst_certificate': 'Upload GST registration certificate (PDF/Image, max 5MB)',
            'pan_card': 'Upload PAN card (PDF/Image, max 5MB)',
            'aadhaar_card': 'Upload Aadhaar card (PDF/Image, max 5MB)',
            'ewaste_authorization': 'Upload the selected authorization document (PDF/Image, max 5MB)',
        }
    
    def clean_gstin_number(self):
        gstin = self.cleaned_data.get('gstin_number', '').upper().strip()
        if gstin:
            import re
            pattern = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')
            if not pattern.match(gstin):
                raise ValidationError("Invalid GSTIN format. Example: 27AABCU9603R1ZM")
        return gstin

    def clean_pan_number(self):
        pan = self.cleaned_data.get('pan_number', '').upper().strip()
        if pan:
            import re
            pattern = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')
            if not pattern.match(pan):
                raise ValidationError("Invalid PAN format. Example: ABCDE1234F")
        return pan

    def clean_aadhaar_number(self):
        aadhaar = self.cleaned_data.get('aadhaar_number', '').strip()
        if aadhaar:
            import re
            # 12 digits, doesn't start with 0 or 1
            pattern = re.compile(r'^[2-9]{1}[0-9]{11}$')
            if not pattern.match(aadhaar):
                raise ValidationError("Invalid Aadhaar format. Must be 12 digits and cannot start with 0 or 1.")
        return aadhaar

    def clean_ewaste_auth_id(self):
        auth_id = self.cleaned_data.get('ewaste_auth_id', '').strip()
        if auth_id:
            # Basic alphanumeric check for IDs, could be more specific depending on auth_type
            import re
            pattern = re.compile(r'^[A-Z0-9/\-]+$')
            if not pattern.match(auth_id.upper()):
                raise ValidationError("Invalid Authorization ID format. Use Alphanumeric characters, slashes, or hyphens.")
        return auth_id
    
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
            'gender', 'contact_person', 'alternate_phone', 'use_registration_details', 
            'date_of_birth', 'address', 'vehicle_type', 'vehicle_number',
            'latitude', 'longitude',
            'driving_license', 'aadhaar_card', 'vehicle_rc',
            'aadhaar_number', 'license_number', 'vehicle_rc_number'
        ]
        widgets = {
            'gender': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500',
                'required': True
            }),
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
            'use_registration_details': forms.CheckboxInput(attrs={
                'id': 'use_registration_details'
            }),
        }
        labels = {
            'date_of_birth': 'Date of Birth *',
            'address': 'Residential Address *',
            'vehicle_type': 'Vehicle Type *',
            'vehicle_number': 'Vehicle Registration Number *',
            'driving_license': 'Driving License *',
            'aadhaar_card': 'Aadhaar Card *',
            'vehicle_rc': 'Vehicle RC *',
        }
        help_texts = {
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

    def clean_aadhaar_number(self):
        aadhaar = self.cleaned_data.get('aadhaar_number', '').strip()
        if aadhaar:
            import re
            # 12 digits, doesn't start with 0 or 1
            pattern = re.compile(r'^[2-9]{1}[0-9]{11}$')
            if not pattern.match(aadhaar):
                raise ValidationError("Invalid Aadhaar format. Must be 12 digits and cannot start with 0 or 1.")
        return aadhaar

    def clean_license_number(self):
        license_num = self.cleaned_data.get('license_number', '').upper().strip()
        if license_num:
            import re
            # DL number format varies slightly but usually 15-16 alphanumeric
            pattern = re.compile(r'^[A-Z]{2}[0-9/]{2,15}$')
            if not pattern.match(license_num):
                raise ValidationError("Invalid Driving License format. e.g., MH01 20200012345")
        return license_num

    def clean_vehicle_rc_number(self):
        rc_num = self.cleaned_data.get('vehicle_rc_number', '').upper().strip()
        if rc_num:
            import re
            # RC number is often same as vehicle number but can be different for some units
            pattern = re.compile(r'^[A-Z]{2}[0-9]{2}[A-Z0-9]{1,6}[0-9]{4}$')
            if not pattern.match(rc_num):
                raise ValidationError("Invalid Vehicle RC format. e.g., MH12AB1234")
        return rc_num
    
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