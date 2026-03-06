"""
Payment models for E-RECYCLO
Complete wallet and transaction system
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone


class Wallet(models.Model):
    """User wallet for earnings"""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
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
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments_wallet'
    
    def __str__(self):
        return f"{self.user.email} - ₹{self.balance}"
    
    def credit(self, amount, description="", photo_post=None):
        """Add money to wallet"""
        self.balance += amount
        self.total_earned += amount
        self.save()
        
        Transaction.objects.create(
            wallet=self,
            transaction_type='credit',
            amount=amount,
            description=description,
            balance_after=self.balance,
            photo_post=photo_post
        )
    
    def debit(self, amount, description="", photo_post=None):
        """Deduct money from wallet"""
        if self.balance >= amount:
            self.balance -= amount
            self.save()
            
            Transaction.objects.create(
                wallet=self,
                transaction_type='debit',
                amount=amount,
                description=description,
                balance_after=self.balance,
                photo_post=photo_post
            )
            return True
        return False


class Transaction(models.Model):
    """Transaction history"""
    
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    
    TRANSACTION_TYPES = [
        ('credit', 'Credit (Money In)'),
        ('debit', 'Debit (Money Out)'),
    ]
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=200)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Optional link to a product/post for product-specific transactions
    photo_post = models.ForeignKey(
        'client.PhotoPost',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payments_transaction'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.wallet.user.email} - {self.transaction_type} ₹{self.amount}"


class WithdrawalRequest(models.Model):
    """Withdrawal requests from users"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='withdrawal_requests'
    )
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    PAYMENT_METHODS = [
        ('bank', 'Bank Transfer'),
        ('upi', 'UPI'),
    ]
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    
    # Bank details
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    ifsc_code = models.CharField(max_length=20, blank=True)
    account_holder_name = models.CharField(max_length=100, blank=True)
    
    # UPI details
    upi_id = models.CharField(max_length=100, blank=True)
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    admin_remarks = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'payments_withdrawalrequest'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - ₹{self.amount} ({self.status})"