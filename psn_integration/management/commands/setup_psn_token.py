# psn_integration/management/commands/setup_psn_token.py
"""
Management command to set up and refresh PSN authentication token
for the dedicated service account
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from psn_integration.models import PSNToken
import requests
import json
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Set up or refresh PSN authentication token for dedicated account'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--npsso',
            type=str,
            help='NPSSO token from PlayStation (required for initial setup)'
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Test the current stored token'
        )
        parser.add_argument(
            '--refresh',
            action='store_true',
            help='Refresh existing token using refresh token'
        )
    
    def handle(self, *args, **options):
        if options['test']:
            self.test_token()
        elif options['refresh']:
            self.refresh_token()
        elif options['npsso']:
            self.setup_new_token(options['npsso'])
        else:
            self.show_help()
    
    def show_help(self):
        """Show setup instructions"""
        self.stdout.write(self.style.SUCCESS("PlayStation Network Token Setup"))
        self.stdout.write("=" * 50)
        self.stdout.write("")
        self.stdout.write("To set up PSN authentication for your dedicated account:")
        self.stdout.write("")
        self.stdout.write("1. Create a dedicated PlayStation account for your service")
        self.stdout.write("2. Login to https://store.playstation.com with that account")
        self.stdout.write("3. Visit https://ca.account.sony.com/api/v1/ssocookie")
        self.stdout.write("4. Copy the npsso token value")
        self.stdout.write("5. Run: python manage.py setup_psn_token --npsso YOUR_TOKEN")
        self.stdout.write("")
        self.stdout.write("Other commands:")
        self.stdout.write("  --test     Test current stored token")
        self.stdout.write("  --refresh  Refresh existing token")
    
    def setup_new_token(self, npsso_token):
        """Set up new PSN token from NPSSO"""
        self.stdout.write("Setting up new PSN token...")
        
        try:
            # Step 1: Get authorization code
            auth_url = "https://ca.account.sony.com/api/authz/v3/oauth/authorize"
            auth_params = {
                "access_type": "offline",
                "client_id": "09515159-7237-4370-9b40-3806e67c0891",
                "response_type": "code",
                "scope": "psn:mobile.v2.core psn:mobile.v2.core.trophy",
                "redirect_uri": "com.scee.psxandroid.scecompcall://redirect"
            }
            
            auth_headers = {
                "Cookie": f"npsso={npsso_token}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            auth_response = requests.get(auth_url, params=auth_params, headers=auth_headers)
            
            if auth_response.status_code != 200:
                raise CommandError(f"Failed to get authorization code: {auth_response.status_code}")
            
            # Extract code from redirect URL
            redirect_url = auth_response.url
            if "code=" not in redirect_url:
                raise CommandError("No authorization code found in response")
            
            # Parse code from URL
            import urllib.parse as urlparse
            parsed_url = urlparse.urlparse(redirect_url)
            query_params = urlparse.parse_qs(parsed_url.query)
            auth_code = query_params.get('code', [None])[0]
            
            if not auth_code:
                raise CommandError("Could not extract authorization code")
            
            self.stdout.write(f"✓ Got authorization code: {auth_code[:20]}...")
            
            # Step 2: Exchange code for access token
            token_url = "https://ca.account.sony.com/api/authz/v3/oauth/token"
            token_data = {
                "code": auth_code,
                "redirect_uri": "com.scee.psxandroid.scecompcall://redirect",
                "grant_type": "authorization_code",
                "token_format": "jwt"
            }
            
            token_headers = {
                "Authorization": "Basic MDk1MTUxNTktNzIzNy00MzcwLTliNDAtMzgwNmU2N2MwODkxOnVjUGprYTV0bnRCMktxc1A=",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            token_response = requests.post(token_url, data=token_data, headers=token_headers)
            
            if token_response.status_code != 200:
                raise CommandError(f"Failed to get access token: {token_response.status_code}")
            
            token_json = token_response.json()
            access_token = token_json.get('access_token')
            refresh_token = token_json.get('refresh_token')
            expires_in = token_json.get('expires_in', 3600)
            
            if not access_token:
                raise CommandError("No access token in response")
            
            self.stdout.write("✓ Got access token")
            
            # Step 3: Test the token by getting user info
            test_url = "https://m.np.playstation.com/api/trophy/v1/users/me/trophySummary"
            test_headers = {
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            test_response = requests.get(test_url, headers=test_headers)
            
            if test_response.status_code != 200:
                raise CommandError(f"Token test failed: {test_response.status_code}")
            
            user_info = test_response.json()
            psn_account_id = user_info.get('accountId')
            trophy_level = user_info.get('trophyLevel')
            
            self.stdout.write(f"✓ Token verified - Account ID: {psn_account_id}, Level: {trophy_level}")
            
            # Step 4: Store the token
            expires_at = timezone.now() + timedelta(seconds=expires_in)
            
            # Deactivate old tokens
            PSNToken.objects.filter(account_type='dedicated', active=True).update(active=False)
            
            # Create new token
            psn_token = PSNToken.objects.create(
                account_type='dedicated',
                access_token=access_token,  # In production, encrypt this
                refresh_token=refresh_token,  # In production, encrypt this
                expires_at=expires_at,
                psn_account_id=psn_account_id,
                active=True
            )
            
            self.stdout.write(self.style.SUCCESS(f"✓ PSN token stored successfully!"))
            self.stdout.write(f"Token expires at: {expires_at}")
            self.stdout.write(f"PSN Account ID: {psn_account_id}")
            self.stdout.write(f"Trophy Level: {trophy_level}")
            
        except Exception as e:
            raise CommandError(f"Error setting up PSN token: {e}")
    
    def test_token(self):
        """Test the current stored token"""
        self.stdout.write("Testing current PSN token...")
        
        try:
            current_token = PSNToken.objects.filter(
                account_type='dedicated',
                active=True
            ).first()
            
            if not current_token:
                self.stdout.write(self.style.ERROR("No active PSN token found"))
                return
            
            if current_token.is_expired():
                self.stdout.write(self.style.WARNING("Token is expired"))
                return
            
            # Test the token
            test_url = "https://m.np.playstation.com/api/trophy/v1/users/me/trophySummary"
            test_headers = {
                "Authorization": f"Bearer {current_token.access_token}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            test_response = requests.get(test_url, headers=test_headers, timeout=10)
            
            if test_response.status_code == 200:
                user_info = test_response.json()
                self.stdout.write(self.style.SUCCESS("✓ Token is working!"))
                self.stdout.write(f"Account ID: {user_info.get('accountId')}")
                self.stdout.write(f"Trophy Level: {user_info.get('trophyLevel')}")
                self.stdout.write(f"Expires at: {current_token.expires_at}")
                
                # Update last used time
                current_token.last_used = timezone.now()
                current_token.save()
                
            else:
                self.stdout.write(self.style.ERROR(f"Token test failed: {test_response.status_code}"))
                self.stdout.write(f"Response: {test_response.text}")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error testing token: {e}"))
    
    def refresh_token(self):
        """Refresh existing token using refresh token"""
        self.stdout.write("Refreshing PSN token...")
        
        try:
            current_token = PSNToken.objects.filter(
                account_type='dedicated',
                active=True
            ).first()
            
            if not current_token or not current_token.refresh_token:
                raise CommandError("No refresh token available. Need to set up new token.")
            
            # Use refresh token to get new access token
            token_url = "https://ca.account.sony.com/api/authz/v3/oauth/token"
            token_data = {
                "refresh_token": current_token.refresh_token,
                "grant_type": "refresh_token",
                "token_format": "jwt"
            }
            
            token_headers = {
                "Authorization": "Basic MDk1MTUxNTktNzIzNy00MzcwLTliNDAtMzgwNmU2N2MwODkxOnVjUGprYTV0bnRCMktxc1A=",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            token_response = requests.post(token_url, data=token_data, headers=token_headers)
            
            if token_response.status_code != 200:
                raise CommandError(f"Failed to refresh token: {token_response.status_code}")
            
            token_json = token_response.json()
            new_access_token = token_json.get('access_token')
            new_refresh_token = token_json.get('refresh_token')
            expires_in = token_json.get('expires_in', 3600)
            
            if not new_access_token:
                raise CommandError("No access token in refresh response")
            
            # Update token
            current_token.access_token = new_access_token
            if new_refresh_token:
                current_token.refresh_token = new_refresh_token
            current_token.expires_at = timezone.now() + timedelta(seconds=expires_in)
            current_token.save()
            
            self.stdout.write(self.style.SUCCESS("✓ Token refreshed successfully!"))
            self.stdout.write(f"New expiration: {current_token.expires_at}")
            
        except Exception as e:
            raise CommandError(f"Error refreshing token: {e}")