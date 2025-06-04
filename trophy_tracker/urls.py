"""
URL configuration for trophy_tracker project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # App URLs
    path('', include('users.urls')),
    path('games/', include('games.urls')),
    path('trophies/', include('trophies.urls')),
    path('rankings/', include('rankings.urls')),
    path('psn/', include('psn_integration.urls')),  # Add PSN integration URLs
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)