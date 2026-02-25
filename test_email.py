"""
DEBUG SCRIPT - Test Email Sending
Run this to diagnose email issues
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

print("=" * 80)
print("EMAIL CONFIGURATION DEBUG")
print("=" * 80)
print()

# Check settings
print("1. EMAIL SETTINGS:")
print(f"   Backend: {settings.EMAIL_BACKEND}")
print(f"   Host: {settings.EMAIL_HOST}")
print(f"   Port: {settings.EMAIL_PORT}")
print(f"   Use TLS: {settings.EMAIL_USE_TLS}")
print(f"   Host User: {settings.EMAIL_HOST_USER}")
print(f"   Host Password: {'*' * len(settings.EMAIL_HOST_PASSWORD) if settings.EMAIL_HOST_PASSWORD else 'NOT SET'}")
print(f"   From Email: {settings.DEFAULT_FROM_EMAIL}")
print()

# Check if backend is console
if 'console' in settings.EMAIL_BACKEND.lower():
    print("❌ ERROR: Email backend is still set to CONSOLE!")
    print("   Your .env file still has:")
    print("   EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend")
    print()
    print("   Change it to:")
    print("   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend")
    print()
    print("   Then restart Django server!")
    print("=" * 80)
    exit(1)

print("✅ Email backend is SMTP (correct)")
print()

# Check credentials
if not settings.EMAIL_HOST_USER:
    print("❌ ERROR: EMAIL_HOST_USER is not set in .env!")
    exit(1)

if not settings.EMAIL_HOST_PASSWORD:
    print("❌ ERROR: EMAIL_HOST_PASSWORD is not set in .env!")
    exit(1)

print("✅ Email credentials are set")
print()

# Test sending
print("2. TESTING EMAIL SEND:")
print("   Attempting to send test email...")
print()

test_email = input("Enter YOUR email address to test: ").strip()

if not test_email:
    print("❌ No email provided!")
    exit(1)

try:
    send_mail(
        subject='🧪 Test Email from E-RECYCLO',
        message='This is a test email. If you receive this, your email configuration is working!',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[test_email],
        fail_silently=False,
    )
    print()
    print("=" * 80)
    print("✅ EMAIL SENT SUCCESSFULLY!")
    print("=" * 80)
    print()
    print(f"Check your inbox: {test_email}")
    print("If you don't see it:")
    print("1. Check spam/junk folder")
    print("2. Wait 1-2 minutes")
    print("3. If still not there, see errors above")
    print()
    
except Exception as e:
    print()
    print("=" * 80)
    print("❌ EMAIL SEND FAILED!")
    print("=" * 80)
    print()
    print(f"Error: {str(e)}")
    print()
    print("Common causes:")
    print()
    print("1. WRONG APP PASSWORD:")
    print("   - Make sure you're using App Password (16 chars)")
    print("   - NOT your regular Gmail password")
    print("   - Generate new one: https://myaccount.google.com/apppasswords")
    print()
    print("2. 2-STEP VERIFICATION NOT ENABLED:")
    print("   - Enable at: https://myaccount.google.com/security")
    print()
    print("3. INCORRECT EMAIL IN .ENV:")
    print("   - EMAIL_HOST_USER must match your Gmail")
    print()
    print("4. FIREWALL BLOCKING PORT 587:")
    print("   - Check your firewall settings")
    print()
    print("=" * 80)
    exit(1)

print("=" * 80)
print("NEXT STEP: Test OTP Registration")
print("=" * 80)
print()
print("If test email arrived, your registration OTP should work!")
print("Try registering with a real email address now.")
print()