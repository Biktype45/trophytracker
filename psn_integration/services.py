# =============================================================================
# File: psn_integration/services.py
# PSN Authentication and API Services
# =============================================================================

import requests
import time
import base64
from urllib.parse import urlencode
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class PSNAuthenticationService:
    """Handle PlayStation Network authentication flow"""
    
    def __init__(self):
        self.client_id = settings.PSN_CLIENT_ID
        self.client_secret = settings.PSN_CLIENT_SECRET
        self.redirect_uri = settings.PSN_REDIRECT_URI
        self.auth_base_url = settings.PSN_AUTH_BASE_URL
        self.api_base_url = settings.PSN_API_BASE_URL
    
    def get_authorization_url(self, state=None):
        """Generate PSN authorization URL"""
        params = {
            'access_type': 'offline',
            'client_id': self.client_id,
            'response_type': 'code',
            'scope': 'psn:mobile.v2.core psn:clientapp',
            'redirect_uri': self.redirect_uri,
        }
        
        if state:
            params['state'] = state
        
        url = f"{self.auth_base_url}/api/authz/v3/oauth/authorize?" + urlencode(params)
        logger.info(f"Generated PSN authorization URL with state: {state}")
        return url
    
    def exchange_code_for_token(self, authorization_code):
        """Exchange authorization code for access token"""
        url = f"{self.auth_base_url}/api/authz/v3/oauth/token"
        
        data = {
            'code': authorization_code,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code',
            'token_format': 'jwt',
        }
        
        headers = {
            'Authorization': f'Basic {self._get_basic_auth()}',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        try:
            logger.info("Exchanging authorization code for PSN token")
            response = requests.post(url, data=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            logger.info("Successfully obtained PSN access token")
            
            return {
                'access_token': token_data['access_token'],
                'refresh_token': token_data['refresh_token'],
                'expires_in': token_data['expires_in'],
                'scope': token_data['scope'],
            }
        
        except requests.RequestException as e:
            logger.error(f"PSN token exchange failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise Exception(f"Failed to exchange authorization code: {e}")
    
    def refresh_access_token(self, refresh_token):
        """Refresh expired access token"""
        url = f"{self.auth_base_url}/api/authz/v3/oauth/token"
        
        data = {
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
            'token_format': 'jwt',
        }
        
        headers = {
            'Authorization': f'Basic {self._get_basic_auth()}',
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        
        try:
            logger.info("Refreshing PSN access token")
            response = requests.post(url, data=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            logger.info("Successfully refreshed PSN access token")
            
            return {
                'access_token': token_data['access_token'],
                'refresh_token': token_data.get('refresh_token', refresh_token),
                'expires_in': token_data['expires_in'],
                'scope': token_data['scope'],
            }
        
        except requests.RequestException as e:
            logger.error(f"PSN token refresh failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise Exception(f"Failed to refresh token: {e}")
    
    def _get_basic_auth(self):
        """Generate basic auth header"""
        credentials = f"{self.client_id}:{self.client_secret}"
        return base64.b64encode(credentials.encode()).decode()

class PSNAPIService:
    """Handle PlayStation Network API calls"""
    
    def __init__(self, access_token):
        self.access_token = access_token
        self.api_base_url = settings.PSN_API_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json',
        })
    
    def get_user_profile(self):
        """Get user's PSN profile summary"""
        url = f"{self.api_base_url}/v1/users/me/trophySummary"
        
        try:
            logger.info("Fetching PSN user profile")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            profile_data = response.json()
            logger.info(f"Successfully retrieved profile for account: {profile_data.get('accountId', 'unknown')}")
            return profile_data
        
        except requests.RequestException as e:
            logger.error(f"Failed to get user profile: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise
    
    def get_user_trophy_titles(self, limit=100, offset=0):
        """Get list of games with trophies for user"""
        url = f"{self.api_base_url}/v1/users/me/trophyTitles"
        
        params = {
            'limit': limit,
            'offset': offset,
        }
        
        try:
            logger.info(f"Fetching trophy titles (limit: {limit}, offset: {offset})")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            titles_data = response.json()
            logger.info(f"Retrieved {len(titles_data.get('trophyTitles', []))} trophy titles")
            return titles_data
        
        except requests.RequestException as e:
            logger.error(f"Failed to get trophy titles: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            raise
    
    def rate_limit_wait(self):
        """Implement rate limiting for PlayStation API"""
        # PlayStation API allows ~300 requests per 15 minutes
        time.sleep(1)  # Conservative rate limiting