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
]