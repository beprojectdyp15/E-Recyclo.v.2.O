"""
Custom user manager for Account model
"""

from django.contrib.auth.models import BaseUserManager


class AccountManager(BaseUserManager):
    """
    Custom manager for Account model
    Handles user creation with email as the unique identifier
    """
    
    def create_user(self, email, username, first_name, last_name, password=None, **extra_fields):
        """
        Create and return a regular user
        """
        if not email:
            raise ValueError('User must have an email address')
        
        if not username:
            raise ValueError('User must have a username')
        
        if not first_name:
            raise ValueError('User must have a first name')
        
        if not last_name:
            raise ValueError('User must have a last name')
        
        # Normalize email
        email = self.normalize_email(email)
        
        # Create user instance
        user = self.model(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            **extra_fields
        )
        
        # Set password (hashed)
        user.set_password(password)
        
        # Save to database
        user.save(using=self._db)
        
        return user
    
    def create_superuser(self, email, username, first_name, last_name, password=None, **extra_fields):
        """
        Create and return a superuser
        """
        # Set superuser flags
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_admin', True)
        
        # Validate superuser flags
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
        
        # Create user
        return self.create_user(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            password=password,
            **extra_fields
        )