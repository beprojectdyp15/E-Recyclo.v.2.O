"""
Custom validators for E-RECYCLO
Password and phone number validation
"""

import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class CustomPasswordValidator:
    """
    Comprehensive password validator
    
    Requirements:
    1. At least 8 characters
    2. Contains uppercase letter
    3. Contains lowercase letter
    4. Contains digit
    5. Contains special character
    6. Not only numbers
    7. Doesn't contain username/name/email
    8. Not a common password
    9. No sequential characters
    10. Maximum 128 characters
    """
    
    def validate(self, password, user=None):
        errors = []
        
        # 1. Length check
        if len(password) < 8:
            errors.append(_("Password must be at least 8 characters long."))
        
        if len(password) > 128:
            errors.append(_("Password must be less than 128 characters."))
        
        # 2. Character type checks
        if not re.search(r'[A-Z]', password):
            errors.append(_("Password must contain at least one uppercase letter."))
        
        if not re.search(r'[a-z]', password):
            errors.append(_("Password must contain at least one lowercase letter."))
        
        if not re.search(r'\d', password):
            errors.append(_("Password must contain at least one digit."))
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/~`]', password):
            errors.append(_("Password must contain at least one special character (!@#$%^&* etc)."))
        
        # 3. Cannot be only numbers
        if password.isdigit():
            errors.append(_("Password cannot contain only numbers."))
        
        # 4. User-specific checks
        if user:
            # Check username
            if hasattr(user, 'username') and user.username:
                if user.username.lower() in password.lower():
                    errors.append(_("Password cannot contain your username."))
            
            # Check first name
            if hasattr(user, 'first_name') and user.first_name and len(user.first_name) >= 3:
                if user.first_name.lower() in password.lower():
                    errors.append(_("Password cannot contain your first name."))
            
            # Check last name
            if hasattr(user, 'last_name') and user.last_name and len(user.last_name) >= 3:
                if user.last_name.lower() in password.lower():
                    errors.append(_("Password cannot contain your last name."))
            
            # Check email
            if hasattr(user, 'email') and user.email:
                email_username = user.email.split('@')[0]
                if len(email_username) >= 3 and email_username.lower() in password.lower():
                    errors.append(_("Password cannot contain your email username."))
        
        # 5. Common passwords
        common_passwords = [
            'password', '12345678', 'qwerty', 'abc12345', 'password123',
            'admin123', 'welcome123', 'test1234', 'letmein', 'monkey',
            'dragon', 'master', 'sunshine', 'princess', 'football',
            'iloveyou', 'welcome', 'login', 'admin', 'root'
        ]
        if password.lower() in common_passwords:
            errors.append(_("This password is too common. Choose a stronger password."))
        
        # 6. Sequential characters
        if self._has_sequential(password):
            errors.append(_("Password cannot contain sequential characters (e.g., 'abc', '123')."))
        
        if errors:
            raise ValidationError(errors, code='password_invalid')
    
    def _has_sequential(self, password):
        """Check for sequential alphabetic or numeric characters"""
        for i in range(len(password) - 2):
            # Check alphabetic sequences
            if password[i:i+3].isalpha():
                chars = password[i:i+3].lower()
                if (ord(chars[1]) == ord(chars[0]) + 1 and 
                    ord(chars[2]) == ord(chars[1]) + 1):
                    return True
            
            # Check numeric sequences
            elif password[i:i+3].isdigit():
                if (int(password[i+1]) == int(password[i]) + 1 and 
                    int(password[i+2]) == int(password[i+1]) + 1):
                    return True
        
        return False
    
    def get_help_text(self):
        return _(
            "Your password must:\n"
            "• Be 8-128 characters long\n"
            "• Contain uppercase and lowercase letters\n"
            "• Contain at least one number\n"
            "• Contain at least one special character\n"
            "• Not contain your username, email, or name\n"
            "• Not be a common password\n"
            "• Not have sequential characters"
        )


def validate_indian_phone(phone):
    """
    Validates Indian phone numbers
    Format: 10 digits starting with 6-9
    """
    # Remove spaces, dashes, parentheses, plus sign
    phone = re.sub(r'[\s\-\(\)\+]', '', phone)
    
    # Remove country code if present
    if phone.startswith('91') and len(phone) == 12:
        phone = phone[2:]
    elif phone.startswith('0') and len(phone) == 11:
        phone = phone[1:]
    
    # Validate format
    if not re.match(r'^[6-9]\d{9}$', phone):
        raise ValidationError(
            _("Enter a valid Indian mobile number (10 digits, starting with 6-9)."),
            code='invalid_phone'
        )
    
    return phone


def validate_file_size(file, max_size_mb=5):
    """
    Validates file size
    Default max size: 5MB
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if file.size > max_size_bytes:
        raise ValidationError(
            _(f"File size cannot exceed {max_size_mb}MB. Current size: {file.size / (1024 * 1024):.2f}MB"),
            code='file_too_large'
        )


def validate_image_file(file):
    """
    Validates that uploaded file is an image
    """
    from PIL import Image
    
    try:
        img = Image.open(file)
        img.verify()
    except Exception:
        raise ValidationError(
            _("Uploaded file is not a valid image."),
            code='invalid_image'
        )