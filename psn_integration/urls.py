# =============================================================================
# File: psn_integration/urls.py
# Complete URL configuration for PSN integration
# =============================================================================

from django.urls import path
from . import views

app_name = 'psn_integration'

urlpatterns = [
    # PSN Authentication
    path('auth/start/', views.psn_auth_start, name='auth_start'),
    path('auth/callback/', views.psn_auth_callback, name='auth_callback'),
    path('connect/', views.psn_connect, name='connect'),
    path('disconnect/', views.psn_disconnect, name='disconnect'),
    
    # PSN Status and Management
    path('status/', views.psn_status, name='status'),
    path('settings/', views.psn_settings, name='settings'),
    
    # Trophy Synchronization
    path('sync/', views.sync_trophies, name='sync_trophies'),
    path('sync/progress/<uuid:job_id>/', views.sync_progress, name='sync_progress'),
    path('sync/cancel/<uuid:job_id>/', views.cancel_sync, name='cancel_sync'),
    path('sync/history/', views.sync_history, name='sync_history'),
    path('sync/details/<uuid:job_id>/', views.sync_details, name='sync_details'),
    
    # PSN Validation (AJAX)
    path('validate/', views.validate_psn_id, name='validate_psn_id'),
    
    # Debug views (development only)
    path('debug/token/', views.debug_psn_token, name='debug_token'),
    path('debug/test-sync/', views.test_sync, name='test_sync'),
]