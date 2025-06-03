# =============================================================================
# File: users/urls.py
# Fixed Users URL Configuration
# =============================================================================

from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Home page
    path('', views.home, name='home'),
    
    # Authentication
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register, name='register'),
    
    # Profile pages (this makes /profile/ work)
    path('profile/', views.profile, name='profile'),
    path('profile/<str:username>/', views.profile, name='profile_detail'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('psn/connect/', views.psn_connection, name='psn_connection'),
    path('psn/sync/', views.sync_trophies, name='sync_trophies'),
    path('psn/sync/status/', views.sync_status, name='sync_status'),
    path('psn/disconnect/', views.disconnect_psn, name='disconnect_psn'),
    path('psn/settings/', views.psn_connection, name='update_sync_settings'),
]