from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

@login_required
def my_trophy_collection(request):
    return HttpResponse("Your trophy collection - Coming soon!")

@login_required
def sync_trophies(request):
    return HttpResponse("Trophy sync - Coming soon!")
