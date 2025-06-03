from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from .models import User
from .forms import CustomUserCreationForm, UserProfileForm

def home(request):
    """Homepage with featured games and top users"""
    from games.models import Game
    from rankings.models import UserRanking
    
    context = {
        'featured_games': Game.objects.order_by('-updated_at')[:6],
        'top_users': User.objects.order_by('-total_trophy_score')[:10],
        'total_users': User.objects.count(),
        'total_games': Game.objects.count(),
    }
    return render(request, 'users/home.html', context)

class CustomUserCreateView(CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('users:profile')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, f'Welcome, {self.object.username}! Your account has been created.')
        return response

@login_required
def profile_view(request):
    """User profile with trophy statistics"""
    user = request.user
    
    # Calculate user statistics
    from trophies.models import UserGameProgress
    
    context = {
        'user': user,
        'level_name': user.get_trophy_level_name(),
        'progress_percentage': user.level_progress_percentage,
        'completed_games': UserGameProgress.objects.filter(user=user, completed=True).count(),
        'total_games': UserGameProgress.objects.filter(user=user).count(),
        'recent_progress': UserGameProgress.objects.filter(user=user).order_by('-last_updated')[:5],
    }
    return render(request, 'users/profile.html', context)

@login_required
def profile_edit(request):
    """Edit user profile"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('users:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'users/profile_edit.html', {'form': form})
