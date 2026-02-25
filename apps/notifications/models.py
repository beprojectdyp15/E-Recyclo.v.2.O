"""
Notification models for E-RECYCLO
"""

from django.db import models
from django.conf import settings


class Notification(models.Model):
    """
    General notification model
    Can be extended later for push notifications
    """
    
    NOTIFICATION_TYPES = [
        ('email', 'Email Notification'),
        ('push', 'Push Notification'),
        ('sms', 'SMS Notification'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    
    is_read = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'notifications_notification'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.subject}"