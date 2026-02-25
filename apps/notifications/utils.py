"""
Email utility functions for E-RECYCLO
Supports both console backend (development) and Brevo (production)
"""

from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def send_verification_email(user):
    """
    Send email verification OTP
    Works with both console and SMTP backends
    """
    try:
        # Get or create email verification
        from apps.accounts.models import EmailVerification
        email_verification, created = EmailVerification.objects.get_or_create(user=user)
        
        # Generate new OTP
        otp = email_verification.generate_otp()
        
        # Prepare email context
        context = {
            'user': user,
            'otp': otp,
            'expires_in': '10 minutes',
            'year': timezone.now().year
        }
        
        # Render HTML email
        html_message = render_to_string('emails/verify_email.html', context)
        
        # Plain text version
        plain_message = f"""
Hi {user.get_full_name()},

Thank you for registering with E-RECYCLO!

Your email verification code is:

{otp}

This code will expire in 10 minutes.

Important:
- Don't share this code with anyone
- If you didn't request this, please ignore this email

Thanks,
E-RECYCLO Team

---
This is an automated email. Please do not reply.
Questions? Contact: support@erecyclo.com
        """.strip()
        
        # Send email
        subject = '🌿 Verify Your Email - E-RECYCLO'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user.email]
        
        # Use EmailMultiAlternatives for HTML email
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=from_email,
            to=recipient_list
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"Verification email sent to {user.email}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
        return False


def send_profile_approved_email(user):
    """
    Send email when profile is approved
    """
    try:
        context = {
            'user': user,
            'dashboard_url': 'http://localhost:8000',  # Update with actual domain
            'year': timezone.now().year
        }
        
        html_message = render_to_string('emails/profile_approved.html', context)
        
        plain_message = f"""
Hi {user.get_full_name()},

Great news! Your profile has been verified and approved by our admin team.

You now have full access to E-RECYCLO!

What you can do now:
"""
        
        if user.is_vendor:
            plain_message += """
- Accept e-waste collection requests
- Generate assessment reports
- Process recyclable materials
- View earnings and analytics
"""
        elif user.is_collector:
            plain_message += """
- View nearby pickup requests
- Accept and collect e-waste
- Earn from deliveries
- Track your earnings
"""
        
        plain_message += """

Thank you for joining E-RECYCLO in making the world greener! 🌿

Best regards,
E-RECYCLO Team
        """.strip()
        
        subject = '🎉 Your Profile is Approved - E-RECYCLO'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user.email]
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=from_email,
            to=recipient_list
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"Approval email sent to {user.email}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send approval email to {user.email}: {str(e)}")
        return False


def send_profile_rejected_email(user, reason):
    """
    Send email when profile is rejected
    """
    try:
        context = {
            'user': user,
            'reason': reason,
            'year': timezone.now().year
        }
        
        plain_message = f"""
Hi {user.get_full_name()},

We have reviewed your profile submission, but unfortunately we cannot approve it at this time.

Reason: {reason}

What to do next:
1. Login to your account
2. Update your profile with the correct information
3. Resubmit for approval

If you have any questions, please contact our support team.

Best regards,
E-RECYCLO Team
        """.strip()
        
        subject = 'Profile Submission - Action Required - E-RECYCLO'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user.email]
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False
        )
        
        logger.info(f"Rejection email sent to {user.email}")
        
        return True
    
    except Exception as e:
        logger.error(f"Failed to send rejection email to {user.email}: {str(e)}")
        return False


def send_welcome_email(user):
    """
    Send welcome email after successful registration
    """
    try:
        plain_message = f"""
Hi {user.get_full_name()},

Welcome to E-RECYCLO! 🌿

We're excited to have you join us in making Maharashtra greener by responsibly recycling e-waste.

Your account has been created successfully. Here's what you can do:
"""
        
        if user.is_client:
            plain_message += """
- Upload photos of your e-waste
- Get instant AI-powered value estimates
- Schedule pickups at your convenience
- Earn money while helping the environment
"""
        elif user.is_vendor:
            plain_message += """
- Receive e-waste collection requests
- Manage your recycling operations
- Generate reports and invoices
- Track your business analytics
"""
        elif user.is_collector:
            plain_message += """
- View available pickup requests nearby
- Accept and complete pickups
- Earn money for each collection
- Track your earnings
"""
        
        plain_message += """

Get Started:
1. Login to your account
2. Complete your profile (if required)
3. Start recycling!

Questions? Contact us at support@erecyclo.com

Best regards,
E-RECYCLO Team
        """.strip()
        
        subject = 'Welcome to E-RECYCLO! 🌿'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user.email]
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=True  # Don't fail if welcome email doesn't send
        )
        
        logger.info(f"Welcome email sent to {user.email}")
        
        return True
    
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
        return False