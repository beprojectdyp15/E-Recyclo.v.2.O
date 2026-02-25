"""
Vendor forms
"""

from django import forms
from apps.client.models import PhotoPost


class AcceptItemForm(forms.Form):
    """
    Form for accepting e-waste item
    """
    
    final_value = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-nature-500',
            'placeholder': 'Enter final value in ₹'
        }),
        label='Final Value (₹)'
    )
    
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-nature-500',
            'rows': 3,
            'placeholder': 'Any remarks about the item (optional)'
        }),
        label='Remarks'
    )


class RejectItemForm(forms.Form):
    """
    Form for rejecting e-waste item
    """
    
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-nature-500',
            'rows': 3,
            'placeholder': 'Please provide a reason for rejection'
        }),
        label='Rejection Reason'
    )