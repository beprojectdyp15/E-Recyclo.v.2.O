"""
Collector forms
"""

from django import forms


class AcceptPickupForm(forms.Form):
    """
    Form for accepting pickup
    """
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-nature-500',
            'rows': 3,
            'placeholder': 'Any notes for the pickup (optional)'
        }),
        label='Notes'
    )


class CompletePickupForm(forms.Form):
    """
    Form for completing pickup
    """
    
    proof_photo = forms.ImageField(
        widget=forms.FileInput(attrs={
            'class': 'hidden',
            'id': 'proof-upload',
            'accept': 'image/*'
        }),
        label='Proof Photo'
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-nature-500',
            'rows': 3,
            'placeholder': 'Any notes about the pickup'
        }),
        label='Notes'
    )