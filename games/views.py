from django.shortcuts import render
from django.http import HttpResponse

def game_list(request):
    return HttpResponse("Games list - Coming soon!")

def game_detail(request, np_communication_id):
    return HttpResponse(f"Game detail for {np_communication_id} - Coming soon!")

def game_search(request):
    return HttpResponse("Game search - Coming soon!")
