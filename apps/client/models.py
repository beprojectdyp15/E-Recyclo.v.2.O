"""
Client app models for E-RECYCLO
Complete e-waste upload and gamification system
"""

from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import math
from apps.ai_services.category_mapper import CategoryMapper


# ============================================
# PHOTO POST MODEL (E-Waste Upload)
# ============================================

class PhotoPost(models.Model):
    """
    E-waste upload by clients
    Includes AI classification and vendor assignment
    """
    
    # User who uploaded
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='photo_posts',
        limit_choices_to={'is_client': True}
    )
    
    # E-Waste Photo
    photo = models.ImageField(
        upload_to='e-photos/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])],
        help_text="Photo of e-waste item"
    )
    
    # User Description
    title = models.CharField(
        max_length=200,
        help_text="Brief title/description"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description (optional)"
    )
    quantity = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(1000)],
        help_text="Number of items"
    )
    
    # Location
    address = models.TextField(help_text="Pickup address")
    latitude = models.FloatField(help_text="GPS latitude")
    longitude = models.FloatField(help_text="GPS longitude")
    
    # Weight and Size (for collector vehicle matching)
    WEIGHT_CHOICES = [
        ('light', 'Light (< 5 kg)'),
        ('medium', 'Medium (5-20 kg)'),
        ('heavy', 'Heavy (20-50 kg)'),
        ('very_heavy', 'Very Heavy (> 50 kg)'),
    ]
    estimated_weight = models.CharField(
        max_length=20,
        choices=WEIGHT_CHOICES,
        blank=True,
        help_text="Approximate weight of the item"
    )
    
    SIZE_CHOICES = [
        ('small', 'Small (fits in backpack)'),
        ('medium', 'Medium (fits on bike)'),
        ('large', 'Large (needs auto/van)'),
        ('very_large', 'Very Large (needs tempo/truck)'),
    ]
    item_size = models.CharField(
        max_length=20,
        choices=SIZE_CHOICES,
        blank=True,
        help_text="Approximate size of the item"
    )
    
    # AI Classification Results
    ai_category = models.CharField(
        max_length=50,
        blank=True,
        choices=CategoryMapper.get_category_choices(), 
        help_text="AI-detected category"
    )
    
    ai_condition = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('excellent', 'Excellent (Like New)'),
            ('good', 'Good (Minor Wear)'),
            ('fair', 'Fair (Some Damage)'),
            ('poor', 'Poor (Not Working)'),
        ],
        help_text="AI-detected condition"
    )
    
    ai_estimated_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="AI estimated value in ₹"
    )
    
    ai_confidence = models.FloatField(
        default=0.0,
        help_text="AI prediction confidence (0-100)"
    )
    
    # Add these fields to PhotoPost model:
    evaluation_type = models.CharField(
        max_length=20,
        choices=[
            ('repair', 'Repairable'),
            ('recycle', 'Recyclable'),
            ('ecopoints', 'Eco-Points Only'),
        ],
        blank=True,
        help_text="Vendor's evaluation after inspection"
    )
    eco_points_awarded = models.IntegerField(
        default=0,
        help_text="Eco-points if item has no monetary value"
    )
    evaluation_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When vendor evaluated the item"
    )
    
    # Pricing Tier (auto-assigned based on value)
    TIER_CHOICES = [
        ('high', 'High Value (₹500+)'),
        ('medium', 'Medium Value (₹100-499)'),
        ('low', 'Low Value (<₹100)'),
    ]
    tier = models.CharField(
        max_length=10,
        choices=TIER_CHOICES,
        blank=True,
        help_text="Pricing tier"
    )
    
    # Assignment Status
    STATUS_CHOICES = [
        ('pending',                 'Pending Vendor Assignment'),
        ('assigned',                'Assigned to Vendor'),
        ('accepted',                'Accepted by Vendor'),
        ('pickup_scheduled',        'Pickup Scheduled'),
        ('in_transit',              'In Transit'),
        ('collected',               'Delivered to Vendor'),
        ('under_review',            'Offer Under Review'),
        ('return_requested',        'Return Requested'),
        ('return_pickup_scheduled', 'Return Pickup Scheduled'),
        ('return_in_transit',       'Return In Transit'),
        ('returned_to_client',      'Returned to Client'),
        ('completed',               'Completed'),
        ('rejected',                'Rejected'),
    ]
    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    
    # Vendor Assignment
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_posts',
        limit_choices_to={'is_vendor': True}
    )
    vendor_remarks = models.TextField(blank=True)
    vendor_final_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Final value determined by vendor"
    )
    
    # Collector Assignment
    collector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pickup_posts',
        limit_choices_to={'is_collector': True}
    )

    # Vendor evaluation detail fields
    condition_notes = models.TextField(
        blank=True,
        help_text="Vendor's physical condition observations"
    )
    price_breakdown = models.TextField(
        blank=True,
        help_text="How vendor calculated the offer price"
    )

    # Offer/rejection tracking
    offer_count = models.IntegerField(default=0)
    rejection_count = models.IntegerField(default=0)
    vendor_declined_reevaluation = models.BooleanField(default=False)

    # Return flow
    return_collector = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='return_pickups',
        limit_choices_to={'is_collector': True}
    )
    return_pickup_otp = models.CharField(max_length=6, blank=True, default='')
    return_delivery_otp = models.CharField(max_length=6, blank=True, default='')

    # OTP Verification
    pickup_otp = models.CharField(
        max_length=6, blank=True, default='',
        help_text="6-digit OTP shown to client; collector enters at pickup to verify identity"
    )
    delivery_otp = models.CharField(
        max_length=6, blank=True, default='',
        help_text="6-digit OTP shown to vendor; collector enters at delivery to confirm handover"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'client_photopost'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['tier']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"
    
    def save(self, *args, **kwargs):
        import random
        # Auto-assign tier based on AI estimated value
        if self.ai_estimated_value:
            if self.ai_estimated_value >= 500:
                self.tier = 'high'
            elif self.ai_estimated_value >= 100:
                self.tier = 'medium'
            else:
                self.tier = 'low'

        # Auto-generate OTPs when collector is first assigned
        if self.collector_id and not self.pickup_otp:
            self.pickup_otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        if self.collector_id and not self.delivery_otp:
            self.delivery_otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])

        if self.return_collector_id and not self.return_pickup_otp:
            self.return_pickup_otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        if self.return_collector_id and not self.return_delivery_otp:
            self.return_delivery_otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        super().save(*args, **kwargs)
    
    def get_final_value(self):
        """Get final value (vendor value if set, else AI estimate)"""
        return self.vendor_final_value or self.ai_estimated_value or Decimal('0.00')
    
    def get_status_badge_class(self):
        """Get CSS class for status badge"""
        status_classes = {
            'pending':           'bg-yellow-100 text-yellow-800',
            'assigned':          'bg-blue-100 text-blue-800',
            'accepted':          'bg-green-100 text-green-800',
            'pickup_scheduled':  'bg-purple-100 text-purple-800',
            'in_transit':        'bg-orange-100 text-orange-800',
            'collected':         'bg-indigo-100 text-indigo-800',
            'under_review':      'bg-purple-100 text-purple-800',
            'completed':         'bg-green-100 text-green-800',
            'rejected':          'bg-red-100 text-red-800',
            'returned_to_client':     'bg-teal-100 text-teal-800',
            'return_requested':       'bg-orange-100 text-orange-800',
            'return_pickup_scheduled':'bg-orange-100 text-orange-800',
            'return_in_transit':      'bg-orange-100 text-orange-800',
        }
        return status_classes.get(self.status, 'bg-gray-100 text-gray-800')


# ============================================
# BULK PICKUP MODEL
# ============================================

class BulkPickup(models.Model):
    """
    Bulk pickup for low-value items (5+ items)
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bulk_pickups',
        limit_choices_to={'is_client': True}
    )
    
    # Pickup Details
    title = models.CharField(max_length=200, default="Bulk E-Waste Pickup")
    address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    
    # Items (low-value PhotoPosts linked to this bulk pickup)
    items = models.ManyToManyField(PhotoPost, related_name='bulk_pickup_group')
    item_count = models.IntegerField(default=0)
    
    # Status
    STATUS_CHOICES = [
        ('collecting', 'Collecting Items (< 5)'),
        ('ready', 'Ready for Pickup (5+)'),
        ('scheduled', 'Pickup Scheduled'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='collecting'
    )
    
    ready_for_pickup = models.BooleanField(default=False)
    
    # Collector Assignment
    collector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bulk_collections',
        limit_choices_to={'is_collector': True}
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'client_bulkpickup'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Bulk Pickup - {self.user.email} ({self.item_count} items)"
    
    def update_item_count(self):
        """Update item count and check if ready for pickup"""
        self.item_count = self.items.count()
        
        if self.item_count >= 5 and not self.ready_for_pickup:
            self.status = 'ready'
            self.ready_for_pickup = True
        elif self.item_count < 5:
            self.status = 'collecting'
            self.ready_for_pickup = False
        
        self.save()
    
    def get_progress_percentage(self):
        """Get progress towards 5 items"""
        return min((self.item_count / 5) * 100, 100)


# ============================================
# COLLECTION CENTER MODEL
# ============================================

class CollectionCenter(models.Model):
    """
    Physical drop-off locations for low-value e-waste
    """
    
    # Center Details
    name = models.CharField(max_length=200)
    address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    
    # Contact
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    
    # Operating Hours
    opening_time = models.TimeField(default='09:00')
    closing_time = models.TimeField(default='18:00')
    
    WEEKDAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    operating_days = models.JSONField(
        default=list,
        help_text="List of operating days"
    )
    
    # Capacity
    is_active = models.BooleanField(default=True)
    max_daily_capacity = models.IntegerField(default=50)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'client_collectioncenter'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def distance_from(self, latitude, longitude):
        """
        Calculate distance from given coordinates using Haversine formula
        Returns distance in kilometers
        """
        from math import radians, sin, cos, sqrt, atan2
        
        # Earth's radius in kilometers
        R = 6371.0
        
        lat1 = radians(latitude)
        lon1 = radians(longitude)
        lat2 = radians(self.latitude)
        lon2 = radians(self.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        distance = R * c
        return round(distance, 2)
    
    def is_open_now(self):
        """Check if center is currently open"""
        from datetime import datetime
        
        if not self.is_active:
            return False
        
        now = timezone.now()
        current_time = now.time()
        current_day = now.strftime('%A').lower()
        
        if current_day not in self.operating_days:
            return False
        
        return self.opening_time <= current_time <= self.closing_time


# ============================================
# APPRECIATION POINTS MODEL
# ============================================

class AppreciationPoints(models.Model):
    """
    Gamification system for client engagement
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='appreciation_points',
        limit_choices_to={'is_client': True}
    )
    
    # Points
    total_points = models.IntegerField(default=0)
    lifetime_points = models.IntegerField(default=0)
    
    # Statistics
    items_recycled = models.IntegerField(default=0)
    total_earned = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Tier/Level
    TIER_CHOICES = [
        ('casual', 'Casual Recycler'),
        ('regular', 'Regular Recycler'),
        ('champion', 'Eco Champion'),
        ('hero', 'Eco Hero'),
        ('legend', 'Eco Legend'),
    ]
    current_tier = models.CharField(
        max_length=20,
        choices=TIER_CHOICES,
        default='casual'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'client_appreciationpoints'
    
    def __str__(self):
        return f"{self.user.email} - {self.total_points} points"
    
    def add_points(self, points, reason=""):
        """Add points and update tier"""
        self.total_points += points
        self.lifetime_points += points
        self.update_tier()
        self.save()
        
        # Create transaction record
        PointTransaction.objects.create(
            user=self.user,
            points=points,
            transaction_type='earn',
            reason=reason
        )
    
    def deduct_points(self, points, reason=""):
        """Deduct points (for redemption, etc.)"""
        if self.total_points >= points:
            self.total_points -= points
            self.save()
            
            PointTransaction.objects.create(
                user=self.user,
                points=-points,
                transaction_type='redeem',
                reason=reason
            )
            return True
        return False
    
    def update_tier(self):
        """Update tier based on lifetime points"""
        if self.lifetime_points >= 10000:
            self.current_tier = 'legend'
        elif self.lifetime_points >= 5000:
            self.current_tier = 'hero'
        elif self.lifetime_points >= 2000:
            self.current_tier = 'champion'
        elif self.lifetime_points >= 500:
            self.current_tier = 'regular'
        else:
            self.current_tier = 'casual'
    
    def get_next_tier_info(self):
        """Get info about next tier"""
        tiers = {
            'casual': {'next': 'regular', 'required': 500},
            'regular': {'next': 'champion', 'required': 2000},
            'champion': {'next': 'hero', 'required': 5000},
            'hero': {'next': 'legend', 'required': 10000},
            'legend': {'next': None, 'required': None},
        }
        
        tier_info = tiers.get(self.current_tier)
        if tier_info['next']:
            remaining = tier_info['required'] - self.lifetime_points
            return {
                'next_tier': tier_info['next'],
                'points_needed': max(0, remaining),
                'progress_percentage': min((self.lifetime_points / tier_info['required']) * 100, 100)
            }
        return None


# ============================================
# POINT TRANSACTION MODEL
# ============================================

class PointTransaction(models.Model):
    """
    Audit trail for all point transactions
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='point_transactions'
    )
    
    points = models.IntegerField(help_text="Positive for earn, negative for redeem")
    
    TRANSACTION_TYPES = [
        ('earn', 'Earned Points'),
        ('redeem', 'Redeemed Points'),
        ('bonus', 'Bonus Points'),
        ('adjustment', 'Admin Adjustment'),
    ]
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    
    reason = models.CharField(max_length=200, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'client_pointtransaction'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.points} points ({self.transaction_type})"


# ============================================
# EVALUATION HISTORY MODEL
# ============================================

class EvaluationHistory(models.Model):
    """Every vendor offer is logged here, even after rejection."""
    post = models.ForeignKey(
        PhotoPost, on_delete=models.CASCADE, related_name='evaluation_history'
    )
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='evaluation_records'
    )
    evaluation_type    = models.CharField(max_length=20, blank=True)
    vendor_final_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    eco_points_awarded = models.IntegerField(default=0)
    vendor_remarks     = models.TextField(blank=True)
    condition_notes    = models.TextField(blank=True)
    price_breakdown    = models.TextField(blank=True)
    evaluated_at       = models.DateTimeField(auto_now_add=True)
    rejected_by_client = models.BooleanField(default=False)
    rejection_reason   = models.TextField(blank=True)

    class Meta:
        db_table = 'client_evaluationhistory'
        ordering = ['-evaluated_at']

    def __str__(self):
        return f"Offer #{self.pk} — ₹{self.vendor_final_value or 0} for '{self.post.title}'"