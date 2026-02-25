"""
Main URL configuration for E-RECYCLO
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.accounts import views as account_views

urlpatterns = [
    # Home
    path('', account_views.home_view, name='home'),
    
    # Django Admin
    path('admin/', admin.site.urls),
    
    # Apps
    path('accounts/', include('apps.accounts.urls')),
    path('client/', include('apps.client.urls')),
    path('vendor/', include('apps.vendor.urls')),
    path('collector/', include('apps.collector.urls')),
    path('admin-panel/', include('apps.admin_custom.urls')),
    path('payments/', include('apps.payments.urls')),
    path('api/', include('apps.ai_services.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom admin site headers
admin.site.site_header = "E-RECYCLO Administration"
admin.site.site_title = "E-RECYCLO Admin"
admin.site.index_title = "Welcome to E-RECYCLO Administration"