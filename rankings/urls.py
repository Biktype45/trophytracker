from django.urls import path
from . import views

app_name = 'rankings'

urlpatterns = [
    path('', views.global_rankings, name='global_rankings'),
    path('leaderboards/', views.leaderboards_overview, name='leaderboards_overview'),
]