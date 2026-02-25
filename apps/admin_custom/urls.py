"""
Admin custom URLs
"""

from django.urls import path
from . import views

app_name = 'admin_custom'

urlpatterns = [
    path("", views.dashboard, name="admin_home"),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('pending-approvals/', views.pending_approvals, name='pending_approvals'),
    path('approve/<int:pk>/', views.approve_profile, name='approve_profile'),
    path('reject/<int:pk>/', views.reject_profile, name='reject_profile'),
    path('users/', views.users, name='users'),
    path('analytics/', views.analytics, name='analytics'),
]