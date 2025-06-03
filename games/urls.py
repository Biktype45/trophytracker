from django.urls import path
from . import views

app_name = 'games'

urlpatterns = [
    path('', views.game_list, name='game_list'),
    path('<str:np_communication_id>/', views.game_detail, name='game_detail'),
    path('search/', views.game_search, name='game_search'),
]