# =============================================================================
# File: users/views.py - CORRECTED FOR PSNAWPService
# Complete Users Views with PSNAWP Integration
# =============================================================================

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.exceptions import ValidationError

# Import PSNAWPService (corrected import)
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
        user = request.user
        
        # Handle basic fields
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

@login_required
def psn_connection(request):
    """Handle PSN ID connection and validation"""
    
    if request.method == 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # AJAX request for PSN ID validation
            return handle_psn_validation(request)
        else:
            # Regular form submission for settings update
            return handle_psn_settings_update(request)
    
    # GET request - show connection page
    context = {
        'user': request.user,
    }
    
    # Add recent sync jobs if user has PSN connected
    if request.user.psn_id:
        context['recent_jobs'] = PSNSyncJob.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]
    
    return render(request, 'users/psn_connection.html', context)

def handle_psn_validation(request):
    """Handle AJAX PSN ID validation - CORRECTED for PSNAWPService"""
    try:
        psn_id = request.POST.get('psn_id', '').strip()
        profile_public = request.POST.get('profile_public') == 'on'
        
        if not psn_id:
            return JsonResponse({
                'success': False,
                'message': 'PSN ID is required'
            })
        
        if not profile_public:
            return JsonResponse({
                'success': False,
                'message': 'Profile must be set to public for trophy syncing'
            })
        
        # Validate PSN ID format
        if len(psn_id) < 3 or len(psn_id) > 16:
            return JsonResponse({
                'success': False,
                'message': 'PSN ID must be between 3 and 16 characters'
            })
        
        # Check if PSN ID is already taken by another user
        if User.objects.filter(psn_id=psn_id).exclude(id=request.user.id).exists():
            return JsonResponse({
                'success': False,
                'message': 'This PSN ID is already connected to another account'
            })
        
        # Use PSNAWPService to validate the ID (CORRECTED METHOD NAME)
        try:
            psn_service = PSNAWPService()
            validation_result = psn_service.validate_psn_user(psn_id)  # CORRECTED: validate_psn_user, not validate_psn_id
        except Exception as e:
            logger.error(f"Error initializing PSNAWPService: {e}")
            return JsonResponse({
                'success': False,
                'message': 'PSN service unavailable. Please try again later.'
            })
        
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
            
            # Update user with PSN info
            request.user.psn_id = psn_id
            request.user.psn_avatar_url = validation_result.get('avatar_url', '')
            request.user.psn_account_id = validation_result.get('account_id', '')
            request.user.profile_public = True  # CORRECTED: use profile_public instead of psn_profile_public
            request.user.allow_trophy_sync = True  # Enable trophy sync
            request.user.save()
            
            logger.info(f"PSN ID {psn_id} successfully connected to user {request.user.username}")
            
            return JsonResponse({
                'success': True,
                'message': 'PSN ID successfully connected! You can now sync your trophies.',
                'psn_data': {
                    'display_name': validation_result.get('display_name', psn_id),
                    'trophy_level': validation_result.get('trophy_level', 1),
                    'avatar_url': validation_result.get('avatar_url', ''),
                    'total_trophies': validation_result.get('total_trophies', {})
                }
            })
        else:
            # Store failed validation
            PSNUserValidation.objects.update_or_create(
                psn_id=psn_id,
                defaults={
                    'validation_status': 'error',
                    'is_valid': False,
                    'is_public': False,
                    'last_error': validation_result.get('error', 'Validation failed')
                }
            )
            
            return JsonResponse({
                'success': False,
                'message': validation_result.get('error', 'PSN ID validation failed')
            })
            
    except Exception as e:
        logger.error(f"Error validating PSN ID for user {request.user.username}: {e}")
        return JsonResponse({
            'success': False,
            'message': 'An unexpected error occurred. Please try again.'
        })

def handle_psn_settings_update(request):
    """Handle PSN settings form submission - CORRECTED for PSNAWPService"""
    try:
        sync_enabled = request.POST.get('sync_enabled') == 'on'
        new_psn_id = request.POST.get('psn_id', '').strip()
        
        # Update sync settings (CORRECTED field name)
        request.user.allow_trophy_sync = sync_enabled
        
        # Update PSN ID if changed
        if new_psn_id != request.user.psn_id:
            if new_psn_id:
                # Validate new PSN ID
                try:
                    psn_service = PSNAWPService()
                    validation_result = psn_service.validate_psn_user(new_psn_id)  # CORRECTED method name
                    
                    if validation_result['valid']:
                        request.user.psn_id = new_psn_id
                        request.user.psn_account_id = validation_result.get('account_id', '')
                        request.user.psn_avatar_url = validation_result.get('avatar_url', '')
                        messages.success(request, f'PSN ID updated to {new_psn_id}')
                    else:
                        messages.error(request, f'Invalid PSN ID: {validation_result.get("error", "Validation failed")}')
                        return redirect('users:psn_connection')
                except Exception as e:
                    logger.error(f"Error validating PSN ID during update: {e}")
                    messages.error(request, 'PSN service unavailable. Please try again later.')
                    return redirect('users:psn_connection')
            else:
                # Clear PSN ID
                request.user.psn_id = None
                request.user.psn_account_id = None
                request.user.psn_avatar_url = None
                request.user.profile_public = False
                messages.info(request, 'PSN ID removed from your account')
        
        request.user.save()
        messages.success(request, 'PSN settings updated successfully')
        
    except Exception as e:
        logger.error(f"Error updating PSN settings for user {request.user.username}: {e}")
        messages.error(request, 'Error updating settings. Please try again.')
    
    return redirect('users:psn_connection')

@login_required
@require_http_methods(["POST"])
def sync_trophies(request):
    """Start trophy synchronization for user - CORRECTED for PSNAWPService"""
    
    # Check if user can sync (CORRECTED field names)
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
        
        # Start sync using the corrected method
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
def disconnect_psn(request):
    """Disconnect PSN account from user"""
    try:
        request.user.psn_id = None
        request.user.psn_account_id = None
        request.user.psn_avatar_url = None
        request.user.profile_public = False
        request.user.allow_trophy_sync = False
        request.user.save()
        
        messages.success(request, 'PlayStation Network account disconnected successfully')
        logger.info(f"User {request.user.username} disconnected PSN account")
        
    except Exception as e:
        logger.error(f"Error disconnecting PSN for user {request.user.username}: {e}")
        messages.error(request, 'Error disconnecting PSN account. Please try again.')
    
    return redirect('users:psn_connection')