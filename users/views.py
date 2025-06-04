# =============================================================================
# File: users/views.py - FIXED VERSION
# Updated Users Views with CustomLoginView and cleaned up imports
# =============================================================================

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from .forms import PSNRegistrationForm

# Import PSNAWPService
from psn_integration.services import PSNAWPService
from psn_integration.models import PSNSyncJob, PSNUserValidation
import logging

logger = logging.getLogger(__name__)

# Import trophy models
try:
    from trophies.models import UserTrophy, UserGameProgress
except ImportError:
    UserTrophy = None
    UserGameProgress = None

try:
    from games.models import Game
except ImportError:
    Game = None

User = get_user_model()

class CustomLoginView(LoginView):
    """Custom login view with redirect logic"""
    template_name = 'users/login.html'
    success_url = reverse_lazy('users:profile')
    redirect_authenticated_user = True
    
    def get_success_url(self):
        # Redirect to profile after successful login
        return reverse_lazy('users:profile')
    
    def form_valid(self, form):
        """Handle successful login"""
        response = super().form_valid(form)
        user = form.get_user()
        messages.success(self.request, f'Welcome back, {user.username}!')
        return response
    
    def form_invalid(self, form):
        """Handle failed login"""
        messages.error(self.request, 'Invalid username or password.')
        return super().form_invalid(form)

def home(request):
    """Home page view with featured content"""
    
    # Get some sample data for the home page
    total_users = User.objects.count()
    total_games = Game.objects.count() if Game else 0
    
    # Get top users for leaderboard preview
    top_users = User.objects.filter(
        total_trophy_score__gt=0
    ).order_by('-total_trophy_score')[:10]
    
    # Get featured games (high difficulty or popular)
    featured_games = []
    if Game:
        featured_games = Game.objects.filter(
            difficulty_multiplier__gte=5.0
        ).order_by('-difficulty_multiplier')[:6]
        
        # If no high-difficulty games, get any games
        if not featured_games:
            featured_games = Game.objects.all()[:6]
    
    context = {
        'total_users': total_users,
        'total_games': total_games,
        'top_users': top_users,
        'featured_games': featured_games,
    }
    return render(request, 'users/home.html', context)

def register(request):
    """Simplified registration with PSN ID"""
    if request.method == 'POST':
        form = PSNRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome to Trophy Tracker, {user.username}!')
            return redirect('users:sync_progress')
    else:
        form = PSNRegistrationForm()
    
    return render(request, 'users/register.html', {'form': form})

def sync_progress(request):
    """Show trophy sync progress page"""
    if not request.user.is_authenticated:
        return redirect('users:login')
    
    # Start sync automatically if user just registered
    if request.user.psn_id and not request.user.last_trophy_sync:
        try:
            psn_service = PSNAWPService()
            sync_job = psn_service.sync_user_trophies(request.user, request.user.psn_id)
            
            return render(request, 'users/sync_progress.html', {
                'sync_job_id': str(sync_job.job_id),
                'auto_start': True
            })
        except Exception as e:
            logger.error(f"Error starting auto-sync for {request.user.username}: {e}")
            messages.error(request, 'Error starting trophy sync. You can try again from your profile.')
            return redirect('users:profile')
    
    return render(request, 'users/sync_progress.html')

def profile(request, username=None):
    """User profile view"""
    if username:
        profile_user = get_object_or_404(User, username=username)
    else:
        if not request.user.is_authenticated:
            return redirect('users:login')
        profile_user = request.user
    
    # Check if profile is public (if viewing someone else's profile)
    if username and username != request.user.username:
        if not profile_user.profile_public:
            messages.error(request, 'This profile is private.')
            return redirect('users:home')
    
    # Get trophy statistics
    total_trophies = (profile_user.bronze_count + profile_user.silver_count + 
                     profile_user.gold_count + profile_user.platinum_count)
    
    # Get recent trophy activity
    recent_trophies = []
    if UserTrophy:
        recent_trophies = UserTrophy.objects.filter(
            user=profile_user, 
            earned=True,
            earned_datetime__isnull=False
        ).select_related('trophy__game').order_by('-earned_datetime')[:10]
    
    # Get game progress
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
        'is_own_profile': profile_user == request.user if request.user.is_authenticated else False,
    }
    
    return render(request, 'users/profile.html', context)

@login_required
def profile_edit(request):
    """Edit profile page"""
    if request.method == 'POST':
        # Handle profile updates
        user = request.user
        
        # Update basic info
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        
        # Validate and update username
        if username and username != user.username:
            if not User.objects.filter(username=username).exclude(id=user.id).exists():
                user.username = username
            else:
                messages.error(request, 'Username already taken')
                return redirect('users:profile_edit')
        
        # Update other fields
        if email:
            user.email = email
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        
        # Update preferences
        user.profile_public = request.POST.get('profile_public') == 'on'
        user.show_rare_trophies = request.POST.get('show_rare_trophies') == 'on'
        user.allow_trophy_sync = request.POST.get('allow_trophy_sync') == 'on'
        
        user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('users:profile')
    
    return render(request, 'users/profile_edit.html', {'user': request.user})

def public_profile(request, username):
    """Public profile view"""
    return profile(request, username=username)

@login_required
def settings(request):
    """User settings page"""
    if request.method == 'POST':
        # Handle PSN ID update
        new_psn_id = request.POST.get('psn_id', '').strip()
        
        if new_psn_id and new_psn_id != request.user.psn_id:
            try:
                # Validate new PSN ID
                psn_service = PSNAWPService()
                validation_result = psn_service.validate_psn_user(new_psn_id)
                
                if validation_result['valid']:
                    request.user.psn_id = new_psn_id
                    request.user.psn_account_id = validation_result.get('account_id', '')
                    request.user.psn_avatar_url = validation_result.get('avatar_url', '')
                    request.user.save()
                    messages.success(request, f'PSN ID updated to {new_psn_id}')
                else:
                    messages.error(request, f'Invalid PSN ID: {validation_result.get("error", "Validation failed")}')
            except Exception as e:
                logger.error(f"Error validating PSN ID: {e}")
                messages.error(request, 'PSN service unavailable. Please try again later.')
        
        # Handle other settings
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        
        if username and username != request.user.username:
            if not User.objects.filter(username=username).exclude(id=request.user.id).exists():
                request.user.username = username
            else:
                messages.error(request, 'Username already taken')
        
        if email:
            request.user.email = email
        
        # Update preferences
        request.user.allow_trophy_sync = request.POST.get('auto_sync') == 'on'
        request.user.profile_public = request.POST.get('public_profile') == 'on'
        
        request.user.save()
        messages.success(request, 'Settings updated successfully!')
        return redirect('users:settings')
    
    # Get recent sync jobs
    recent_jobs = PSNSyncJob.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5] if request.user.psn_id else []
    
    context = {
        'user': request.user,
        'recent_jobs': recent_jobs,
    }
    
    return render(request, 'users/settings.html', context)

def user_logout(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('users:home')

@login_required
@require_http_methods(["POST"])
def sync_trophies(request):
    """Start trophy synchronization for user"""
    
    # Check if user can sync
    if not request.user.psn_id or not request.user.allow_trophy_sync:
        return JsonResponse({
            'success': False,
            'message': 'Cannot sync trophies. Please connect your PSN account first.'
        })
    
    # Check for existing running sync job
    existing_job = PSNSyncJob.objects.filter(
        user=request.user,
        status__in=['pending', 'running']
    ).first()
    
    if existing_job:
        return JsonResponse({
            'success': False,
            'message': 'A sync job is already running. Please wait for it to complete.',
            'job_id': str(existing_job.job_id)
        })
    
    try:
        # Initialize PSN service
        psn_service = PSNAWPService()
        
        # Start sync
        sync_job = psn_service.sync_user_trophies(request.user, request.user.psn_id)
        
        # Update user sync timestamp
        request.user.last_trophy_sync = timezone.now()
        request.user.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Trophy sync completed!',
            'job_id': str(sync_job.job_id),
            'stats': {
                'games_found': sync_job.games_found,
                'games_created': sync_job.games_created,
                'games_updated': sync_job.games_updated,
                'trophies_synced': sync_job.trophies_synced,
                'trophies_new': sync_job.trophies_new,
                'score_gained': sync_job.score_gained(),
                'levels_gained': sync_job.level_gained()
            }
        })
        
    except Exception as e:
        logger.error(f"Error starting trophy sync for user {request.user.username}: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error starting trophy sync: {str(e)}'
        })

@login_required
def sync_status(request):
    """Get status of current sync job"""
    job_id = request.GET.get('job_id')
    
    if not job_id:
        return JsonResponse({'error': 'Job ID required'}, status=400)
    
    try:
        sync_job = PSNSyncJob.objects.get(
            job_id=job_id,
            user=request.user
        )
        
        return JsonResponse({
            'status': sync_job.status,
            'progress': sync_job.progress_percentage,
            'current_task': sync_job.current_task,
            'games_found': sync_job.games_found,
            'games_created': sync_job.games_created,
            'games_updated': sync_job.games_updated,
            'trophies_synced': sync_job.trophies_synced,
            'trophies_new': sync_job.trophies_new,
            'score_before': sync_job.score_before,
            'score_after': sync_job.score_after,
            'score_gained': sync_job.score_gained(),
            'level_before': sync_job.level_before,
            'level_after': sync_job.level_after,
            'levels_gained': sync_job.level_gained(),
            'error_message': sync_job.error_message,
            'started_at': sync_job.started_at.isoformat() if sync_job.started_at else None,
            'completed_at': sync_job.completed_at.isoformat() if sync_job.completed_at else None,
        })
        
    except PSNSyncJob.DoesNotExist:
        return JsonResponse({'error': 'Sync job not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return JsonResponse({'error': 'Error getting sync status'}, status=500)

@login_required
@require_http_methods(["POST"])
def validate_psn_id(request):
    """AJAX endpoint to validate PSN ID"""
    psn_id = request.POST.get('psn_id', '').strip()
    
    if not psn_id:
        return JsonResponse({
            'success': False,
            'message': 'PSN ID is required'
        })
    
    # Check if PSN ID is already taken
    if User.objects.filter(psn_id=psn_id).exclude(id=request.user.id).exists():
        return JsonResponse({
            'success': False,
            'message': 'This PSN ID is already connected to another account'
        })
    
    try:
        # Validate with PlayStation Network
        psn_service = PSNAWPService()
        validation_result = psn_service.validate_psn_user(psn_id)
        
        if validation_result['valid']:
            # Store validation result
            PSNUserValidation.objects.update_or_create(
                psn_id=psn_id,
                defaults={
                    'validation_status': 'valid',
                    'is_valid': True,
                    'is_public': True,
                    'psn_account_id': validation_result.get('account_id', ''),
                    'display_name': validation_result.get('display_name', psn_id),
                    'avatar_url': validation_result.get('avatar_url', ''),
                    'trophy_level': validation_result.get('trophy_level', 1),
                    'total_trophies': validation_result.get('total_trophies', {}),
                    'trophy_points': validation_result.get('trophy_points', 0),
                    'last_error': ''
                }
            )
            
            return JsonResponse({
                'success': True,
                'message': 'PSN ID is valid and accessible!',
                'psn_data': {
                    'display_name': validation_result.get('display_name', psn_id),
                    'trophy_level': validation_result.get('trophy_level', 1),
                    'avatar_url': validation_result.get('avatar_url', ''),
                    'total_trophies': validation_result.get('total_trophies', {})
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'message': validation_result.get('error', 'PSN ID validation failed')
            })
            
    except Exception as e:
        logger.error(f"Error validating PSN ID {psn_id}: {e}")
        return JsonResponse({
            'success': False,
            'message': 'PSN service unavailable. Please try again later.'
        })

@login_required
@require_http_methods(["POST"])
def disconnect_psn(request):
    """Disconnect PSN account from user"""
    try:
        request.user.psn_id = None
        request.user.psn_account_id = None
        request.user.psn_avatar_url = None
        request.user.allow_trophy_sync = False
        request.user.save()
        
        messages.success(request, 'PlayStation Network account disconnected successfully')
        logger.info(f"User {request.user.username} disconnected PSN account")
        
    except Exception as e:
        logger.error(f"Error disconnecting PSN for user {request.user.username}: {e}")
        messages.error(request, 'Error disconnecting PSN account. Please try again.')
    
    return redirect('users:settings')