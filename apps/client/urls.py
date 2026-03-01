"""
Client URL patterns
"""

from django.urls import path
from . import views

app_name = 'client'

urlpatterns = [
    path('dashboard/',                        views.dashboard,            name='dashboard'),
    path('upload/',                           views.upload_ewaste,        name='upload_ewaste'),
    path('my-uploads/',                       views.my_uploads,           name='my_uploads'),
    path('upload/<int:pk>/',                  views.upload_detail,        name='upload_detail'),
    path('upload/<int:pk>/review-offer/',     views.review_offer,         name='review_offer'),
    path('upload/<int:pk>/request-return/',   views.request_return,       name='request_return'),
    path('upload/<int:pk>/accept-last-offer/', views.accept_last_offer,   name='accept_last_offer'),
    path('upload/<int:pk>/transfer-vendor/',  views.transfer_to_vendor,   name='transfer_to_vendor'),
    path('upload/<int:pk>/certificate/',      views.download_certificate, name='download_certificate'),
    path('wallet/',                           views.wallet,               name='wallet'),
    path('wallet/download/',                  views.download_statement,   name='download_statement'),
    path('collection-centers/',              views.collection_centers,   name='collection_centers'),
    path('bulk-pickup/',                      views.bulk_pickup,          name='bulk_pickup'),
]
