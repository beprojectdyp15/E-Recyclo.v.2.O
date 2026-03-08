"""
Collector URLs
"""

from django.urls import path
from . import views

app_name = 'collector'

urlpatterns = [
    path('dashboard/',                        views.dashboard,            name='dashboard'),
    path('available-pickups/',                views.available_pickups,    name='available_pickups'),
    path('update-location/',                  views.update_location,      name='update_location'),   # ← NEW
    path('accept-pickup/<int:pk>/',           views.accept_pickup,        name='accept_pickup'),
    path('my-pickups/',                       views.my_pickups,           name='my_pickups'),
    path('complete/<int:pk>/',                views.complete_pickup,      name='complete_pickup'),
    path('verify-pickup-otp/<int:pk>/',       views.verify_pickup_otp,    name='verify_pickup_otp'),
    path('verify-delivery-otp/<int:pk>/',     views.verify_delivery_otp,  name='verify_delivery_otp'),
    path('pickup/<int:pk>/',                  views.pickup_detail,        name='pickup_detail'),
    path('start-trip/<int:pk>/',              views.start_trip,           name='start_trip'),
    path('earnings/',                         views.earnings,             name='earnings'),
    path('earnings/download/',                views.download_statement,   name='download_statement'),
]


