# =============================================================================
# File: psn_integration/urls.py
# Real PSN Integration URLs
# =============================================================================

from django.urls import path
from . import views

app_name = 'psn_integration'

urlpatterns = [
    # Authentication flow
    path('auth/start/', views.psn_auth_start, name='psn_auth_start'),
    path('auth/callback/', views.psn_auth_callback, name='psn_auth_callback'),
    path('disconnect/', views.psn_disconnect, name='psn_disconnect'),
    
    # Trophy sync and status
    path('sync/', views.sync_trophies, name='sync_trophies'),
    path('status/', views.psn_status, name='psn_status'),
]