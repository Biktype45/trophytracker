# =============================================================================
# File: users/views.py
# Complete Users Views with Profile Support
# =============================================================================

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth import get_user_model

# Import trophy models
try:
    from trophies.models import UserTrophy, UserGameProgress
except ImportError:
    # Handle case where trophies app isn't ready yet
    UserTrophy = None
    UserGameProgress = None

try:
    from games.models import Game
except ImportError:
    # Handle case where games app isn't ready yet
    Game = None

User = get_user_model()

def home(request):
    """Home page view"""
    context = {
        'total_users': User.objects.count(),
        'total_games': Game.objects.count() if Game else 0,
    }
    return render(request, 'users/home.html', context)

def profile(request, username=None):
    """User profile view"""
    if username:
        profile_user = get_object_or_404(User, username=username)
    else:
        if not request.user.is_authenticated:
            return redirect('users:login')
        profile_user = request.user
    
    # Get trophy statistics
    total_trophies = (profile_user.bronze_count + profile_user.silver_count + 
                     profile_user.gold_count + profile_user.platinum_count)
    
    # Get recent trophy activity (if models are available)
    recent_trophies = []
    if UserTrophy:
        recent_trophies = UserTrophy.objects.filter(
            user=profile_user, 
            earned=True,
            earned_datetime__isnull=False
        ).select_related('trophy__game').order_by('-earned_datetime')[:10]
    
    # Get game progress (if models are available)
    game_progress = []
    if UserGameProgress:
        game_progress = UserGameProgress.objects.filter(
            user=profile_user
        ).select_related('game').order_by('-last_updated')[:10]
    
    context = {
        'profile_user': profile_user,
        'total_trophies': total_trophies,
        'recent_trophies': recent_trophies,
        'game_progress': game_progress,
    }
    
    return render(request, 'users/profile.html', context)

@login_required
def profile_edit(request):
    """Edit user profile"""
    if request.method == 'POST':
        # Basic profile edit logic - you can enhance this later
        user = request.user
        
        # For now, just handle basic fields
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        email = request.POST.get('email', '')
        
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('users:profile')
    
    return render(request, 'users/profile_edit.html', {'user': request.user})

def user_login(request):
    """User login view"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                return redirect('users:profile')
        messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'users/login.html', {'form': form})

def user_logout(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('users:home')

def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            login(request, user)
            return redirect('users:profile')
    else:
        form = UserCreationForm()
    
    return render(request, 'users/register.html', {'form': form})