# =============================================================================
# File: psn_integration/views.py
# PSN Authentication Views - Phase 1 (Basic Authentication Only)
# =============================================================================

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import PSNToken, PSNSyncLog
from .services import PSNAuthenticationService, PSNAPIService
import uuid
import logging

logger = logging.getLogger(__name__)

@login_required
def psn_auth_start(request):
    """Start PSN authentication flow"""
    # Generate state for CSRF protection
    state = str(uuid.uuid4())
    request.session['psn_auth_state'] = state
    
    logger.info(f"Starting PSN authentication for user: {request.user.username}")
    
    try:
        auth_service = PSNAuthenticationService()
        authorization_url = auth_service.get_authorization_url(state=state)
        
        logger.info(f"Redirecting to PSN authorization URL")
        return redirect(authorization_url)
        
    except Exception as e:
        logger.error(f"Failed to start PSN authentication: {e}")
        messages.error(request, "Failed to start PlayStation Network authentication. Please try again.")
        return redirect('users:profile')

@login_required
def psn_auth_callback(request):
    """Handle PSN authentication callback"""
    # Verify state parameter
    received_state = request.GET.get('state')
    expected_state = request.session.get('psn_auth_state')
    
    if not received_state or received_state != expected_state:
        logger.warning(f"PSN auth state mismatch for user {request.user.username}")
        messages.error(request, "Invalid authentication state. Please try again.")
        return redirect('users:profile')
    
    # Clean up session
    if 'psn_auth_state' in request.session:
        del request.session['psn_auth_state']
    
    # Check for authorization error
    error = request.GET.get('error')
    if error:
        error_description = request.GET.get('error_description', 'Unknown error')
        logger.warning(f"PSN auth error for user {request.user.username}: {error} - {error_description}")
        messages.error(request, f"PlayStation Network authentication failed: {error_description}")
        return redirect('users:profile')
    
    # Get authorization code
    authorization_code = request.GET.get('code')
    if not authorization_code:
        logger.warning(f"No authorization code received for user {request.user.username}")
        messages.error(request, "No authorization code received. Please try again.")
        return redirect('users:profile')
    
    try:
        # Exchange code for token
        auth_service = PSNAuthenticationService()
        token_data = auth_service.exchange_code_for_token(authorization_code)
        
        # Get user profile to extract PSN information
        api_service = PSNAPIService(token_data['access_token'])
        profile_data = api_service.get_user_profile()
        
        # Calculate token expiration
        expires_at = timezone.now() + timedelta(seconds=token_data['expires_in'])
        
        # Store or update PSN token
        psn_token, created = PSNToken.objects.update_or_create(
            user=request.user,
            defaults={
                'psn_account_id': profile_data['accountId'],
                'psn_online_id': profile_data.get('onlineId', ''),
                'psn_avatar_url': '',  # We'll get this later when we implement full profile sync
                'token_type': 'Bearer',
                'expires_at': expires_at,
                'scope': token_data['scope'],
                'is_active': True,
                'sync_errors': 0,
            }
        )
        
        # Store encrypted tokens
        psn_token.set_access_token(token_data['access_token'])
        psn_token.set_refresh_token(token_data['refresh_token'])
        psn_token.save()
        
        # Update user profile with PSN information
        request.user.psn_id = profile_data.get('onlineId', '')
        request.user.psn_account_id = profile_data['accountId']
        request.user.save()
        
        action = "linked" if created else "updated"
        logger.info(f"PSN account {action} for user {request.user.username}: {psn_token.psn_online_id}")
        messages.success(request, f"PlayStation Network account successfully {action}! PSN ID: {psn_token.psn_online_id}")
        
        return redirect('users:profile')
        
    except Exception as e:
        logger.error(f"PSN authentication error for user {request.user.id}: {e}")
        messages.error(request, "Failed to link PlayStation Network account. Please try again.")
        return redirect('users:profile')

@login_required
def psn_disconnect(request):
    """Disconnect PSN account"""
    try:
        psn_token = PSNToken.objects.get(user=request.user)
        psn_online_id = psn_token.psn_online_id
        psn_token.delete()
        
        # Clear PSN data from user profile
        request.user.psn_id = None
        request.user.psn_account_id = None
        request.user.psn_avatar_url = None
        request.user.save()
        
        logger.info(f"PSN account disconnected for user {request.user.username}: {psn_online_id}")
        messages.success(request, f"PlayStation Network account ({psn_online_id}) disconnected successfully.")
        
    except PSNToken.DoesNotExist:
        logger.info(f"PSN disconnect attempted but no token found for user {request.user.username}")
        messages.info(request, "No PlayStation Network account was linked.")
    
    return redirect('users:profile')

@login_required
def psn_status(request):
    """Show PSN connection status and basic info"""
    context = {
        'psn_connected': False,
        'psn_token': None,
    }
    
    try:
        psn_token = PSNToken.objects.get(user=request.user, is_active=True)
        context.update({
            'psn_connected': True,
            'psn_token': psn_token,
            'token_expired': psn_token.is_expired(),
        })
    except PSNToken.DoesNotExist:
        pass
    
    return render(request, 'psn_integration/status.html', context)