"""
URL patterns for accounts app
"""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Home
    path('', views.home_view, name='home'),
    
    # Registration
    path('register/', views.register_view, name='register'),
    path('verify-email/', views.verify_email_view, name='verify_email'),
    path('resend-otp/', views.resend_otp_view, name='resend_otp'),
    
    # Login/Logout
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Forgot Password (NEW)
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('verify-reset-otp/', views.verify_reset_otp_view, name='verify_reset_otp'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    
    # Profile Completion
    path('complete-vendor-profile/', views.complete_vendor_profile, name='complete_vendor_profile'),
    path('complete-collector-profile/', views.complete_collector_profile, name='complete_collector_profile'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    
    # AJAX
    path('check-username/', views.check_username_view, name='check_username'),
    path('cleanup-registration/', views.cleanup_registration_view, name='cleanup_registration'),
]
