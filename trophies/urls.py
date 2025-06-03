from django.urls import path
from . import views

app_name = 'trophies'

urlpatterns = [
    path('my-collection/', views.my_trophy_collection, name='my_collection'),
    path('sync/', views.sync_trophies, name='sync_trophies'),
]