from django.shortcuts import render
from django.http import HttpResponse

def global_rankings(request):
    return HttpResponse("Global rankings - Coming soon!")

def leaderboards_overview(request):
    return HttpResponse("Leaderboards - Coming soon!")