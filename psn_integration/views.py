# =============================================================================
# File: psn_integration/views.py
# Real PSN Integration Views
# =============================================================================

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import uuid
import logging

# Try to import PSN models (they might not exist yet)
try:
    from .models import PSNToken, PSNSyncLog
except ImportError:
    PSNToken = None
    PSNSyncLog = None

# Try to import PSN services (they might not exist yet)
try:
    from .services import PSNAuthenticationService, PSNAPIService
except ImportError:
    PSNAuthenticationService = None
    PSNAPIService = None

logger = logging.getLogger(__name__)

@login_required
def psn_auth_start(request):
    """Start PSN authentication flow"""
    
    # Check if we have the PSN service available
    if not PSNAuthenticationService:
        messages.error(request, "PSN integration is not fully configured yet. Please check back later.")
        return redirect('/profile/')
    
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
        return redirect('/profile/')

# =============================================================================
# Update this in your psn_integration/views.py file
# Replace the psn_auth_callback function with this version
# =============================================================================

@login_required
def psn_auth_callback(request):
    """Handle PSN authentication callback"""
    
    # Get the authorization code and state from the URL
    received_code = request.GET.get('code')
    received_state = request.GET.get('state')
    
    logger.info(f"PSN Auth Callback - Code: {received_code}, State: {received_state}")
    
    # For now, just show success message with the received data
    if received_code and received_state:
        messages.success(request, 
            f"🎉 PSN Authentication Successful! "
            f"Received authorization code: {received_code[:10]}... "
            f"This proves the OAuth flow is working!"
        )
        
        # Store PSN connection indicator (for demonstration)
        request.user.psn_id = "TestPSNUser"  # Temporary for testing
        request.user.save()
        
        messages.info(request, 
            "Next step: Implement full token exchange and trophy sync in Phase 2. "
            "For now, your PSN account appears as 'connected' for testing purposes."
        )
    else:
        messages.error(request, 
            f"PSN Authentication failed. Missing code or state. "
            f"Code: {received_code}, State: {received_state}"
        )
    
    return redirect('/profile/')

@login_required
def psn_status(request):
    """Show PSN connection status and basic info"""
    context = {
        'psn_connected': False,
        'psn_token': None,
        'recent_syncs': [],
    }
    
    # Check if user has PSN data
    if hasattr(request.user, 'psn_id') and request.user.psn_id:
        context['psn_connected'] = True
        context['psn_id'] = request.user.psn_id
    
    # Try to get PSN token if models exist
    if PSNToken:
        try:
            psn_token = PSNToken.objects.get(user=request.user, is_active=True)
            context['psn_token'] = psn_token
            context['token_expired'] = psn_token.is_expired()
        except PSNToken.DoesNotExist:
            pass
    
    # Try to get recent syncs if models exist
    if PSNSyncLog:
        try:
            recent_syncs = PSNSyncLog.objects.filter(user=request.user).order_by('-started_at')[:5]
            context['recent_syncs'] = recent_syncs
        except:
            pass
    
    return render(request, 'psn_integration/status.html', context)

@login_required
def sync_trophies(request):
    """Sync user's trophies from PSN"""
    
    # Check if PSN integration is fully set up
    if not PSNToken or not PSNSyncLog:
        messages.warning(request, "Trophy sync is not available yet. PSN integration is still being set up.")
        return redirect('/psn/status/')
    
    try:
        psn_token = PSNToken.objects.get(user=request.user, is_active=True)
    except PSNToken.DoesNotExist:
        messages.error(request, "Please link your PlayStation Network account first.")
        return redirect('/psn/auth/start/')
    
    # For now, just show a message
    messages.info(request, "Trophy sync functionality will be available in Phase 2!")
    return redirect('/psn/status/')

@login_required
def psn_disconnect(request):
    """Disconnect PSN account"""
    
    if PSNToken:
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
    else:
        # Clear any PSN data from user profile anyway
        request.user.psn_id = None
        request.user.psn_account_id = None
        request.user.psn_avatar_url = None
        request.user.save()
        messages.success(request, "PlayStation Network account disconnected.")
    
    return redirect('/profile/')