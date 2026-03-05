"""
Collector models for E-RECYCLO
"""

from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from decimal import Decimal


class CollectorPickup(models.Model):
    """
    Pickup assignment for collectors
    """
    
    collector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='collector_pickups',
        limit_choices_to={'is_collector': True}
    )
    
    photo_post = models.ForeignKey(
        'client.PhotoPost',
        on_delete=models.CASCADE,
        related_name='collector_pickups'
    )
    
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('accepted', 'Accepted by Collector'),
        ('in_progress', 'Pickup In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='assigned')
    
    # Pickup details
    scheduled_date = models.DateTimeField(null=True, blank=True)
    pickup_date = models.DateTimeField(null=True, blank=True)
    
    # Proof of pickup
    proof_photo = models.ImageField(
        upload_to='collector/proof/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        null=True,
        blank=True,
        help_text="Photo proof of completed pickup"
    )
    
    notes = models.TextField(blank=True)
    
    # Payment
    base_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('50.00')
    )
    
    distance_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    total_payment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('50.00')
    )
    
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('paid', 'Paid'),
        ],
        default='pending'
    )
    
    # Duration tracking
    trip_start_at = models.DateTimeField(null=True, blank=True, help_text="When collector clicked 'Start Trip'")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'collector_collectorpickup'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.collector.email} - {self.photo_post.title} ({self.status})"
    
    def get_total_duration(self):
        """Calculate total trip duration as a human-readable string"""
        if self.trip_start_at and self.completed_at:
            diff = self.completed_at - self.trip_start_at
            total_mins = round(diff.total_seconds() / 60)
            if total_mins < 1:
                return "< 1 min"
            elif total_mins < 60:
                return f"{total_mins} min"
            else:
                hours = total_mins // 60
                mins = total_mins % 60
                if mins == 0:
                    return f"{hours}h"
                return f"{hours}h {mins}m"
        return "—"

    def get_duration_minutes(self):
        """Get raw duration in minutes for calculations"""
        if self.trip_start_at and self.completed_at:
            diff = self.completed_at - self.trip_start_at
            return round(diff.total_seconds() / 60)
        return 0
    
    def calculate_payment(self, distance_km=0):
        """Calculate total payment based on distance"""
        self.distance_fee = Decimal(str(distance_km)) * Decimal('5.00')  # ₹5 per km
        self.total_payment = self.base_fee + self.distance_fee
        self.save()


class CollectorEarnings(models.Model):
    """
    Track collector overall earnings summary (KEEP THIS - DON'T CHANGE)
    """
    
    collector = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='collector_earnings',
        limit_choices_to={'is_collector': True}
    )
    
    total_pickups = models.IntegerField(default=0)
    completed_pickups = models.IntegerField(default=0)
    
    total_earned = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    total_withdrawn = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    available_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'collector_collectorearnings'
    
    def __str__(self):
        return f"{self.collector.email} - ₹{self.available_balance}"
    
    def add_earning(self, amount):
        """Add earnings from completed pickup"""
        self.total_earned += Decimal(str(amount))
        self.available_balance += Decimal(str(amount))
        self.completed_pickups += 1
        self.save()


# ADD THIS NEW MODEL (for tracking individual pickup payments)
class CollectorPickupPayment(models.Model):
    """Track payment details for each individual pickup"""
    
    collector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pickup_payments',
        limit_choices_to={'is_collector': True}
    )
    
    pickup = models.OneToOneField(
        'client.PhotoPost',
        on_delete=models.CASCADE,
        related_name='collector_payment'
    )
    
    # Payment breakdown
    base_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('50.00'))
    distance_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    handling_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    distance_km = models.FloatField(default=0)
    
    # Payment status
    paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'collector_pickup_payment'
        verbose_name = 'Pickup Payment'
        verbose_name_plural = 'Pickup Payments'
    
    def __str__(self):
        return f"₹{self.total_amount} - {self.collector.get_full_name()} - Pickup #{self.pickup.id}"
    
    def mark_as_paid(self):
        """Mark payment as completed and update collector earnings"""
        if not self.paid:
            from django.utils import timezone
            self.paid = True
            self.paid_at = timezone.now()
            self.save()
            
            # Update collector's overall earnings
            earnings, created = CollectorEarnings.objects.get_or_create(
                collector=self.collector
            )
            earnings.add_earning(self.total_amount)