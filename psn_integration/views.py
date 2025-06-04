# =============================================================================
# File: psn_integration/views.py
# Complete PSN Integration Views - Updated for Current Architecture
# =============================================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from datetime import timedelta
import uuid
import logging
import json

# Import models
from .models import PSNToken, PSNSyncJob, PSNUserValidation, PSNApiCall
from users.models import User

# Try to import PSN services
try:
    from .services import PSNAWPService
    PSNAWP_AVAILABLE = True
except ImportError:
    PSNAWP_AVAILABLE = False

logger = logging.getLogger(__name__)

# =============================================================================
# PSN AUTHENTICATION VIEWS
# =============================================================================

@login_required
def psn_auth_start(request):
    """Start PSN authentication flow - simplified for direct PSN ID entry"""
    
    context = {
        'user': request.user,
        'psn_connected': bool(request.user.psn_id),
        'current_psn_id': request.user.psn_id or '',
    }
    
    return render(request, 'psn_integration/auth_start.html', context)

@login_required 
@require_http_methods(["POST"])
def psn_connect(request):
    """Connect PSN account via PSN ID entry"""
    
    psn_id = request.POST.get('psn_id', '').strip()
    
    if not psn_id:
        messages.error(request, "Please enter a valid PlayStation Network ID.")
        return redirect('psn_integration:auth_start')
    
    # Validate PSN ID format (basic validation)
    if len(psn_id) < 3 or len(psn_id) > 16:
        messages.error(request, "PSN ID must be between 3 and 16 characters.")
        return redirect('psn_integration:auth_start')
    
    logger.info(f"Attempting to connect PSN ID {psn_id} for user {request.user.username}")
    
    try:
        # Validate PSN ID if service is available
        if PSNAWP_AVAILABLE:
            psn_service = PSNAWPService()
            validation_result = psn_service.validate_psn_user(psn_id)
            
            if not validation_result['is_valid']:
                messages.error(request, f"PlayStation Network ID '{psn_id}' not found or not accessible.")
                return redirect('psn_integration:auth_start')
            
            if not validation_result['is_public']:
                messages.warning(request, 
                    f"PlayStation Network ID '{psn_id}' is private. "
                    "Please set your profile to public for trophy sync to work properly."
                )
        
        # Update user with PSN information
        request.user.psn_id = psn_id
        if PSNAWP_AVAILABLE and 'account_id' in validation_result:
            request.user.psn_account_id = validation_result.get('account_id', '')
            request.user.psn_avatar_url = validation_result.get('avatar_url', '')
        request.user.save()
        
        messages.success(request, f"✅ Successfully connected PlayStation Network ID: {psn_id}")
        messages.info(request, "You can now sync your trophy data from your profile page.")
        
        return redirect('users:profile')
        
    except Exception as e:
        logger.error(f"Error connecting PSN ID {psn_id}: {e}")
        messages.error(request, f"Failed to connect PlayStation Network account: {str(e)}")
        return redirect('psn_integration:auth_start')

@login_required
def psn_auth_callback(request):
    """Handle PSN authentication callback (for future OAuth implementation)"""
    
    # Get the authorization code and state from the URL
    received_code = request.GET.get('code')
    received_state = request.GET.get('state')
    
    logger.info(f"PSN Auth Callback - Code: {received_code}, State: {received_state}")
    
    if received_code and received_state:
        messages.success(request, 
            "🎉 PSN Authentication successful! "
            "OAuth flow is working. Token exchange will be implemented in Phase 2."
        )
        
        # For now, redirect to PSN connection page
        messages.info(request, "Please enter your PSN ID below to complete the connection.")
        return redirect('psn_integration:auth_start')
    else:
        messages.error(request, "PSN Authentication failed. Please try again.")
        return redirect('psn_integration:auth_start')

# =============================================================================
# PSN STATUS AND MANAGEMENT VIEWS  
# =============================================================================

@login_required
def psn_status(request):
    """Show PSN connection status and sync history"""
    
    context = {
        'user': request.user,
        'psn_connected': bool(request.user.psn_id),
        'psn_id': request.user.psn_id,
        'psn_account_id': request.user.psn_account_id,
        'psn_avatar_url': request.user.psn_avatar_url,
        'last_sync': request.user.last_trophy_sync,
        'recent_syncs': [],
        'validation_status': None,
        'active_token': None,
    }
    
    # Get PSN validation status if available
    if request.user.psn_id:
        try:
            validation = PSNUserValidation.objects.get(psn_id=request.user.psn_id)
            context['validation_status'] = validation
        except PSNUserValidation.DoesNotExist:
            pass
    
    # Get recent sync jobs
    try:
        recent_syncs = PSNSyncJob.objects.filter(
            user=request.user
        ).order_by('-created_at')[:10]
        context['recent_syncs'] = recent_syncs
    except Exception as e:
        logger.error(f"Error fetching sync jobs: {e}")
    
    # Get active PSN token
    try:
        active_token = PSNToken.objects.filter(active=True).first()
        context['active_token'] = active_token
        context['service_available'] = active_token and not active_token.is_expired()
    except Exception as e:
        logger.error(f"Error checking PSN token: {e}")
        context['service_available'] = False
    
    return render(request, 'psn_integration/status.html', context)

# =============================================================================
# TROPHY SYNC VIEWS
# =============================================================================

@login_required
@require_http_methods(["POST"])
def sync_trophies(request):
    """Start trophy synchronization for the user"""
    
    if not request.user.psn_id:
        messages.error(request, "Please connect your PlayStation Network account first.")
        return redirect('psn_integration:auth_start')
    
    if not PSNAWP_AVAILABLE:
        messages.error(request, "Trophy sync service is not available. Please contact support.")
        return redirect('psn_integration:status')
    
    # Check if user has a sync job already running
    active_sync = PSNSyncJob.objects.filter(
        user=request.user,
        status__in=['pending', 'running']
    ).first()
    
    if active_sync:
        messages.warning(request, "A trophy sync is already in progress. Please wait for it to complete.")
        return redirect('psn_integration:status')
    
    # Check if user synced recently (prevent spam)
    recent_sync = PSNSyncJob.objects.filter(
        user=request.user,
        created_at__gte=timezone.now() - timedelta(minutes=5)
    ).first()
    
    if recent_sync:
        messages.warning(request, "Please wait at least 5 minutes between sync attempts.")
        return redirect('psn_integration:status')
    
    try:
        # Create sync job
        sync_job = PSNSyncJob.objects.create(
            user=request.user,
            sync_type='manual',
            priority='normal',
            score_before=request.user.total_trophy_score,
            level_before=request.user.current_trophy_level
        )
        
        # Start the sync process
        psn_service = PSNAWPService()
        success = psn_service.sync_user_trophies(request.user, request.user.psn_id, sync_job)
        
        if success:
            messages.success(request, 
                f"🔄 Trophy sync started successfully! "
                f"Job ID: {sync_job.job_id.hex[:8]}... "
                f"Refresh this page to see progress."
            )
        else:
            messages.error(request, "Failed to start trophy sync. Please try again.")
            
    except Exception as e:
        logger.error(f"Error starting trophy sync for {request.user.username}: {e}")
        messages.error(request, f"Failed to start trophy sync: {str(e)}")
    
    return redirect('psn_integration:status')

@login_required
def sync_progress(request, job_id):
    """Get sync progress via AJAX"""
    
    try:
        sync_job = get_object_or_404(PSNSyncJob, job_id=job_id, user=request.user)
        
        response_data = {
            'status': sync_job.status,
            'progress': sync_job.progress_percentage,
            'current_task': sync_job.current_task,
            'games_found': sync_job.games_found,
            'trophies_synced': sync_job.trophies_synced,
            'errors_count': sync_job.errors_count,
            'duration': sync_job.duration_seconds() if sync_job.completed_at else 0,
        }
        
        # Add results if completed
        if sync_job.status == 'completed':
            response_data.update({
                'score_gained': sync_job.score_gained(),
                'level_gained': sync_job.level_gained(),
                'games_created': sync_job.games_created,
                'final_score': sync_job.score_after,
                'final_level': sync_job.level_after,
            })
        
        return JsonResponse(response_data)
        
    except PSNSyncJob.DoesNotExist:
        return JsonResponse({'error': 'Sync job not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting sync progress: {e}")
        return JsonResponse({'error': 'Failed to get sync progress'}, status=500)

# =============================================================================
# PSN VALIDATION VIEWS
# =============================================================================

@login_required
@require_http_methods(["POST"])
def validate_psn_id(request):
    """Validate PSN ID via AJAX"""
    
    try:
        data = json.loads(request.body)
        psn_id = data.get('psn_id', '').strip()
        
        if not psn_id:
            return JsonResponse({'valid': False, 'error': 'PSN ID is required'})
        
        if not PSNAWP_AVAILABLE:
            return JsonResponse({
                'valid': True, 
                'warning': 'PSN validation service unavailable - ID format looks valid',
                'is_public': True
            })
        
        # Validate using PSN service
        psn_service = PSNAWPService()
        result = psn_service.validate_psn_user(psn_id)
        
        response_data = {
            'valid': result['is_valid'],
            'is_public': result.get('is_public', False),
            'display_name': result.get('display_name', psn_id),
            'avatar_url': result.get('avatar_url', ''),
        }
        
        if not result['is_valid']:
            response_data['error'] = 'PSN ID not found or not accessible'
        elif not result.get('is_public', False):
            response_data['warning'] = 'Profile is private - please set to public for trophy sync'
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({'valid': False, 'error': 'Invalid request format'})
    except Exception as e:
        logger.error(f"Error validating PSN ID: {e}")
        return JsonResponse({'valid': False, 'error': 'Validation service error'})

# =============================================================================
# PSN DISCONNECT AND SETTINGS
# =============================================================================

@login_required
@require_http_methods(["POST"])
def psn_disconnect(request):
    """Disconnect PSN account"""
    
    if not request.user.psn_id:
        messages.info(request, "No PlayStation Network account is currently connected.")
        return redirect('users:profile')
    
    try:
        psn_id = request.user.psn_id
        
        # Clear PSN data from user
        request.user.psn_id = None
        request.user.psn_account_id = None
        request.user.psn_avatar_url = None
        request.user.last_trophy_sync = None
        request.user.save()
        
        # Cancel any pending sync jobs
        PSNSyncJob.objects.filter(
            user=request.user,
            status__in=['pending', 'running']
        ).update(
            status='cancelled',
            completed_at=timezone.now()
        )
        
        logger.info(f"PSN account {psn_id} disconnected for user {request.user.username}")
        messages.success(request, f"PlayStation Network account ({psn_id}) disconnected successfully.")
        
    except Exception as e:
        logger.error(f"Error disconnecting PSN for user {request.user.username}: {e}")
        messages.error(request, "Failed to disconnect PlayStation Network account.")
    
    return redirect('users:profile')

@login_required
def psn_settings(request):
    """PSN integration settings page"""
    
    if request.method == 'POST':
        # Update PSN settings
        allow_sync = request.POST.get('allow_trophy_sync') == 'on'
        profile_public = request.POST.get('profile_public') == 'on'
        show_rare = request.POST.get('show_rare_trophies') == 'on'
        
        request.user.allow_trophy_sync = allow_sync
        request.user.profile_public = profile_public  
        request.user.show_rare_trophies = show_rare
        request.user.save()
        
        messages.success(request, "PSN settings updated successfully.")
        return redirect('psn_integration:settings')
    
    context = {
        'user': request.user,
        'psn_connected': bool(request.user.psn_id),
        'recent_api_calls': [],
    }
    
    # Get recent API calls for debugging
    try:
        if request.user.psn_id:
            recent_calls = PSNApiCall.objects.filter(
                psn_id=request.user.psn_id
            ).order_by('-timestamp')[:10]
            context['recent_api_calls'] = recent_calls
    except Exception as e:
        logger.error(f"Error fetching API calls: {e}")
    
    return render(request, 'psn_integration/settings.html', context)

# =============================================================================
# UTILITY VIEWS
# =============================================================================

@login_required
def sync_history(request):
    """Show detailed sync history for the user"""
    
    sync_jobs = PSNSyncJob.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    # Pagination could be added here
    context = {
        'user': request.user,
        'sync_jobs': sync_jobs[:50],  # Show last 50 syncs
    }
    
    return render(request, 'psn_integration/sync_history.html', context)

@login_required
def sync_details(request, job_id):
    """Show detailed information about a specific sync job"""
    
    sync_job = get_object_or_404(PSNSyncJob, job_id=job_id, user=request.user)
    
    context = {
        'user': request.user,
        'sync_job': sync_job,
    }
    
    return render(request, 'psn_integration/sync_details.html', context)

@login_required
def cancel_sync(request, job_id):
    """Cancel a running sync job"""
    
    if request.method == 'POST':
        try:
            sync_job = get_object_or_404(PSNSyncJob, job_id=job_id, user=request.user)
            
            if sync_job.status in ['pending', 'running']:
                sync_job.status = 'cancelled'
                sync_job.completed_at = timezone.now()
                sync_job.save()
                
                messages.success(request, "Trophy sync cancelled successfully.")
            else:
                messages.warning(request, "Sync job is not running and cannot be cancelled.")
                
        except Exception as e:
            logger.error(f"Error cancelling sync job {job_id}: {e}")
            messages.error(request, "Failed to cancel sync job.")
    
    return redirect('psn_integration:status')

# =============================================================================
# DEBUG AND ADMIN VIEWS (Development only)
# =============================================================================

@login_required
def debug_psn_token(request):
    """Debug view to check PSN token status (development only)"""
    
    if not settings.DEBUG:
        messages.error(request, "Debug views are only available in development mode.")
        return redirect('psn_integration:status')
    
    context = {
        'tokens': PSNToken.objects.all(),
        'recent_api_calls': PSNApiCall.objects.all().order_by('-timestamp')[:20],
        'recent_validations': PSNUserValidation.objects.all().order_by('-last_checked')[:20],
    }
    
    return render(request, 'psn_integration/debug.html', context)

@login_required  
def test_sync(request):
    """Test sync functionality (development only)"""
    
    if not settings.DEBUG:
        messages.error(request, "Test views are only available in development mode.")
        return redirect('psn_integration:status')
    
    if not request.user.psn_id:
        messages.error(request, "Please connect a PSN account first.")
        return redirect('psn_integration:auth_start')
    
    try:
        # Create a test sync job
        sync_job = PSNSyncJob.objects.create(
            user=request.user,
            sync_type='manual',
            priority='high',
            score_before=request.user.total_trophy_score,
            level_before=request.user.current_trophy_level
        )
        
        messages.success(request, f"Test sync job created: {sync_job.job_id}")
        return redirect('psn_integration:sync_details', job_id=sync_job.job_id)
        
    except Exception as e:
        logger.error(f"Error creating test sync: {e}")
        messages.error(request, f"Failed to create test sync: {str(e)}")
        return redirect('psn_integration:status')