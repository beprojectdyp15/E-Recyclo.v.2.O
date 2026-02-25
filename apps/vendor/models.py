"""
Vendor models for E-RECYCLO
"""

from django.db import models
from django.conf import settings
from decimal import Decimal


class VendorAssignment(models.Model):
    """
    Track vendor assignments to e-waste posts
    """
    
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vendor_assignments',
        limit_choices_to={'is_vendor': True}
    )
    
    photo_post = models.ForeignKey(
        'client.PhotoPost',
        on_delete=models.CASCADE,
        related_name='vendor_assignments'
    )
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    final_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Final price offered by vendor"
    )
    
    remarks = models.TextField(
        blank=True,
        help_text="Vendor's remarks about the item"
    )
    
    assigned_collector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_pickups',
        limit_choices_to={'is_collector': True}
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'vendor_vendorassignment'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.vendor.email} - {self.photo_post.title} ({self.status})"


class VendorReport(models.Model):
    """
    Monthly/yearly reports for vendors
    """
    
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vendor_reports',
        limit_choices_to={'is_vendor': True}
    )
    
    PERIOD_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    period_type = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    
    year = models.IntegerField()
    month = models.IntegerField(null=True, blank=True)  # 1-12, null for yearly
    
    total_items_accepted = models.IntegerField(default=0)
    total_items_rejected = models.IntegerField(default=0)
    total_value_processed = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    total_commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'vendor_vendorreport'
        ordering = ['-year', '-month']
        unique_together = ['vendor', 'period_type', 'year', 'month']
    
    def __str__(self):
        if self.month:
            return f"{self.vendor.email} - {self.year}/{self.month}"
        return f"{self.vendor.email} - {self.year}"