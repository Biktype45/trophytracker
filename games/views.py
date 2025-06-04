# =============================================================================
# games/views.py
# =============================================================================
from django.shortcuts import render
from django.http import HttpResponse

def game_list(request):
    return HttpResponse("Game list - Coming soon!")

def game_detail(request, game_id):
    return HttpResponse(f"Game detail for {game_id} - Coming soon!")

