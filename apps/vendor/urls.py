"""
Vendor URLs
"""

from django.urls import path
from . import views

app_name = 'vendor'

urlpatterns = [
    path('dashboard/',                      views.dashboard,            name='dashboard'),
    path('pending-requests/',               views.pending_requests,     name='pending_requests'),
    path('accept/<int:pk>/',                views.accept_item,          name='accept_item'),
    path('reject/<int:pk>/',                views.reject_item,          name='reject_item'),
    path('accepted-items/',                 views.accepted_items,       name='accepted_items'),
    path('evaluate/<int:pk>/',              views.evaluate_item,        name='evaluate_item'),
    path('decline-reevaluation/<int:pk>/',  views.decline_reevaluation, name='decline_reevaluation'),
    path('item/<int:pk>/',                  views.item_detail,          name='item_detail'),
    path('reports/',                        views.reports,              name='reports'),
    path('payment/',                        views.payment,              name='payment'),
    path('payment/download/',               views.download_statement,   name='download_statement'),
]