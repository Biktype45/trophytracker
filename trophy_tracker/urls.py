from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),  # This handles all user-related URLs including profile
    path('games/', include('games.urls')),
    path('trophies/', include('trophies.urls')),
    path('rankings/', include('rankings.urls')),
    path('psn/', include('psn_integration.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)