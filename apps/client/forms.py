"""
Client forms for E-RECYCLO
Complete e-waste upload and profile forms
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import PhotoPost, BulkPickup
from config.validators import validate_indian_phone


class PhotoPostForm(forms.ModelForm):
    """
    Complete e-waste upload form with photo, location, and details
    """
    
    class Meta:
        model = PhotoPost
        fields = [
            'photo', 'title', 'description', 'quantity', 
            'estimated_weight', 'item_size',
            'address', 'latitude', 'longitude'
        ]
        widgets = {
            'photo': forms.FileInput(attrs={
                'class': 'hidden',
                'id': 'photo-upload',
                'accept': 'image/jpeg,image/jpg,image/png,image/webp',
                'required': True
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-nature-500 text-sm',
                'placeholder': 'e.g., Old Smartphone, Broken Laptop, Used TV',
                'required': True,
                'maxlength': 200
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-nature-500 text-sm',
                'rows': 3,
                'placeholder': 'Describe the condition, brand, model, or any other relevant details...',
                'style': 'resize:none'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-nature-500',
                'min': 1,
                'max': 1000,
                'value': 1
            }),
            'estimated_weight': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-nature-500 text-sm',
            }),
            'item_size': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-nature-500 text-sm',
            }),
            'address': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-nature-500 text-sm',
                'rows': 3,
                'placeholder': 'Enter complete pickup address with landmark',
                'required': True,
                'style': 'resize:none'
            }),
            'latitude': forms.HiddenInput(attrs={
                'id': 'latitude',
                'required': True
            }),
            'longitude': forms.HiddenInput(attrs={
                'id': 'longitude',
                'required': True
            }),
        }
        labels = {
            'photo': 'Upload Photo *',
            'title': 'Item Title *',
            'description': 'Description (Optional)',
            'quantity': 'Quantity *',
            'estimated_weight': 'Estimated Weight',
            'item_size': 'Item Size',
            'address': 'Pickup Address *',
        }
        help_texts = {
            'photo': 'Upload a clear photo of your e-waste item (JPG, PNG, or WEBP, max 5MB)',
            'title': 'Give your e-waste item a short, descriptive title',
            'quantity': 'How many items of this type do you have?',
            'estimated_weight': 'Helps us assign the right collector vehicle',
            'item_size': 'Helps us assign the right collector vehicle',
            'address': 'We need this to send a collector to pick up your e-waste',
        }
    
    def clean_title(self):
        """Validate title"""
        title = self.cleaned_data.get('title', '').strip()
        
        if len(title) < 3:
            raise ValidationError("Title must be at least 3 characters long.")
        
        if len(title) > 200:
            raise ValidationError("Title must be less than 200 characters.")
        
        return title
    
    def clean_quantity(self):
        """Validate quantity"""
        quantity = self.cleaned_data.get('quantity')
        
        if quantity < 1:
            raise ValidationError("Quantity must be at least 1.")
        
        if quantity > 1000:
            raise ValidationError("Quantity cannot exceed 1000. For larger quantities, please contact support.")
        
        return quantity
    
    def clean_address(self):
        """Validate address"""
        address = self.cleaned_data.get('address', '').strip()
        
        if len(address) < 10:
            raise ValidationError("Please provide a complete address.")
        
        return address
    
    def clean(self):
        """Validate location coordinates"""
        cleaned_data = super().clean()
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        
        if not latitude or not longitude:
            raise ValidationError("Please select your location on the map or use 'Get My Location' button.")
        
        try:
            lat = float(latitude)
            lng = float(longitude)
            
            # Basic coordinate validation (India bounds approximately)
            if not (6.0 <= lat <= 37.0 and 68.0 <= lng <= 98.0):
                raise ValidationError("Location coordinates seem invalid. Please select a valid location in India.")
        except (ValueError, TypeError):
            raise ValidationError("Invalid location coordinates.")
        
        return cleaned_data


class BulkPickupForm(forms.ModelForm):
    """
    Bulk pickup request form
    """
    
    class Meta:
        model = BulkPickup
        fields = ['title', 'address', 'latitude', 'longitude']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-nature-500',
                'placeholder': 'e.g., Bulk E-Waste Pickup - Office Items'
            }),
            'address': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-nature-500',
                'rows': 2,
                'placeholder': 'Pickup address'
            }),
            'latitude': forms.HiddenInput(attrs={'id': 'bulk-latitude'}),
            'longitude': forms.HiddenInput(attrs={'id': 'bulk-longitude'}),
        }