# psn_integration/management/commands/debug_psn_oauth.py
"""
Complete PSN OAuth setup with NPSSO → Code → Access Token → Trophy Data flow
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from psn_integration.models import PSNToken, PSNApiCall
import requests
import json
from datetime import datetime, timedelta
import urllib.parse as urlparse

class Command(BaseCommand):
    help = 'Complete PSN OAuth flow: NPSSO → Code → Access Token → Trophy Data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--npsso',
            type=str,
            help='NPSSO token from PlayStation'
        )
        parser.add_argument(
            '--full-flow',
            action='store_true',
            help='Run complete OAuth flow and fetch trophy data'
        )
        parser.add_argument(
            '--test-npsso',
            action='store_true',
            help='Test if NPSSO token is valid'
        )
        parser.add_argument(
            '--get-code',
            action='store_true',
            help='Get authorization code from NPSSO'
        )
        parser.add_argument(
            '--code',
            type=str,
            help='Authorization code to exchange for access token'
        )
        parser.add_argument(
            '--test-token',
            action='store_true',
            help='Test existing saved token'
        )
    
    def handle(self, *args, **options):
        if options['full_flow'] and options['npsso']:
            self.run_full_oauth_flow(options['npsso'])
        elif options['test_npsso'] and options['npsso']:
            self.test_npsso_token(options['npsso'])
        elif options['get_code'] and options['npsso']:
            self.get_auth_code_only(options['npsso'])
        elif options['code']:
            self.exchange_code_for_token(options['code'])
        elif options['test_token']:
            self.test_saved_token()
        else:
            self.show_usage_help()
    
    def show_usage_help(self):
        """Show usage instructions"""
        self.stdout.write(self.style.SUCCESS("=== PSN OAuth Complete Flow ==="))
        self.stdout.write("")
        self.stdout.write("🎯 RECOMMENDED: Full automated flow")
        self.stdout.write("python manage.py debug_psn_oauth --full-flow --npsso YOUR_NPSSO_TOKEN")
        self.stdout.write("")
        self.stdout.write("📋 Step-by-step options:")
        self.stdout.write("1. Test NPSSO token:")
        self.stdout.write("   python manage.py debug_psn_oauth --test-npsso --npsso YOUR_TOKEN")
        self.stdout.write("")
        self.stdout.write("2. Get authorization code:")
        self.stdout.write("   python manage.py debug_psn_oauth --get-code --npsso YOUR_TOKEN")
        self.stdout.write("")
        self.stdout.write("3. Exchange code for access token:")
        self.stdout.write("   python manage.py debug_psn_oauth --code YOUR_AUTH_CODE")
        self.stdout.write("")
        self.stdout.write("4. Test saved token:")
        self.stdout.write("   python manage.py debug_psn_oauth --test-token")
        self.stdout.write("")
        self.stdout.write("🔑 To get NPSSO token:")
        self.stdout.write("1. Login to https://store.playstation.com")
        self.stdout.write("2. Visit https://ca.account.sony.com/api/v1/ssocookie")
        self.stdout.write("3. Copy the npsso value")
    
    def run_full_oauth_flow(self, npsso_token):
        """Run the complete OAuth flow: NPSSO → Code → Access Token → Trophy Data"""
        self.stdout.write(self.style.SUCCESS("🚀 Starting complete PSN OAuth flow..."))
        self.stdout.write("")
        
        # Step 1: Test NPSSO
        self.stdout.write("Step 1: Testing NPSSO token...")
        if not self.test_npsso_token(npsso_token):
            self.stdout.write(self.style.ERROR("❌ NPSSO token test failed. Stopping."))
            return False
        
        # Step 2: Get authorization code
        self.stdout.write("\nStep 2: Getting authorization code...")
        auth_code = self.get_auth_code(npsso_token)
        if not auth_code:
            self.stdout.write(self.style.ERROR("❌ Failed to get authorization code. Stopping."))
            return False
        
        # Step 3: Exchange code for access token
        self.stdout.write("\nStep 3: Exchanging code for access token...")
        token_data = self.get_access_token(auth_code)
        if not token_data:
            self.stdout.write(self.style.ERROR("❌ Failed to get access token. Stopping."))
            return False
        
        # Step 4: Save token to database
        self.stdout.write("\nStep 4: Saving token to database...")
        if not self.save_token_to_database(token_data):
            self.stdout.write(self.style.ERROR("❌ Failed to save token. Stopping."))
            return False
        
        # Step 5: Test trophy data fetching
        self.stdout.write("\nStep 5: Testing trophy data fetching...")
        if self.test_trophy_data_fetching(token_data['access_token']):
            self.stdout.write(self.style.SUCCESS("\n🎉 Complete OAuth flow successful!"))
            self.stdout.write("✅ PSN integration is now ready for production use.")
            return True
        else:
            self.stdout.write(self.style.ERROR("❌ Trophy data fetching failed."))
            return False
    
    def test_npsso_token(self, npsso_token):
        """Test if NPSSO token is valid"""
        self.stdout.write("🔍 Testing NPSSO token validity...")
        
        try:
            # Test NPSSO by hitting the ssocookie endpoint
            test_url = "https://ca.account.sony.com/api/v1/ssocookie"
            headers = {
                'Cookie': f'npsso={npsso_token}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(test_url, headers=headers, timeout=10)
            
            if response.status_code == 200 and 'npsso' in response.text:
                self.stdout.write(self.style.SUCCESS("✅ NPSSO token is valid"))
                return True
            else:
                self.stdout.write(self.style.ERROR(f"❌ NPSSO token invalid. Status: {response.status_code}"))
                self.stdout.write(f"Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error testing NPSSO: {e}"))
            return False
    
    def get_auth_code(self, npsso):
        """Get authorization code from NPSSO token"""
        self.stdout.write("🔑 Getting authorization code...")
        
        url = "https://ca.account.sony.com/api/authz/v3/oauth/authorize"
        params = {
            "access_type": "offline",
            "client_id": "09515159-7237-4370-9b40-3806e67c0891",
            "response_type": "code",
            "scope": "psn:mobile.v2.core psn:clientapp",
            "redirect_uri": "com.scee.psxandroid.scecompcall://redirect"
        }
        headers = {
            "Cookie": f"npsso={npsso}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            response = requests.get(url, headers=headers, params=params, allow_redirects=False, timeout=10)
            
            self.stdout.write(f"Authorization response status: {response.status_code}")
            
            if "Location" in response.headers:
                location = response.headers["Location"]
                self.stdout.write(f"Redirect location: {location}")
                
                if "code=" in location:
                    # Extract code from URL
                    code = location.split("code=")[1].split("&")[0]
                    self.stdout.write(self.style.SUCCESS(f"✅ Authorization code obtained: {code[:20]}..."))
                    return code
                else:
                    self.stdout.write(self.style.ERROR("❌ No authorization code in redirect"))
                    return None
            else:
                self.stdout.write(self.style.ERROR("❌ No redirect location in response"))
                self.stdout.write(f"Response body: {response.text[:500]}")
                return None
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error getting auth code: {e}"))
            return None
    
    def get_access_token(self, auth_code):
        """Exchange authorization code for access token"""
        self.stdout.write("🎫 Exchanging code for access token...")
        
        url = "https://ca.account.sony.com/api/authz/v3/oauth/token"
        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": "com.scee.psxandroid.scecompcall://redirect",
            "client_id": "09515159-7237-4370-9b40-3806e67c0891"
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            response = requests.post(url, data=data, headers=headers, timeout=10)
            
            self.stdout.write(f"Token exchange status: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                self.stdout.write(self.style.SUCCESS("✅ Access token obtained successfully"))
                self.stdout.write(f"Token type: {token_data.get('token_type', 'Unknown')}")
                self.stdout.write(f"Expires in: {token_data.get('expires_in', 'Unknown')} seconds")
                self.stdout.write(f"Scope: {token_data.get('scope', 'Unknown')}")
                return token_data
            else:
                self.stdout.write(self.style.ERROR(f"❌ Token exchange failed: {response.status_code}"))
                self.stdout.write(f"Response: {response.text}")
                return None
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error getting access token: {e}"))
            return None
    
    def save_token_to_database(self, token_data):
        """Save access token to database"""
        self.stdout.write("💾 Saving token to database...")
        
        try:
            # Calculate expiration time
            expires_in = token_data.get('expires_in', 3600)
            expires_at = timezone.now() + timedelta(seconds=expires_in)
            
            # Deactivate existing tokens
            PSNToken.objects.filter(account_type='dedicated', active=True).update(active=False)
            
            # Create new token
            psn_token = PSNToken.objects.create(
                account_type='dedicated',
                access_token=token_data['access_token'],
                refresh_token=token_data.get('refresh_token', ''),
                expires_at=expires_at,
                psn_username='dedicated_service_account',
                active=True
            )
            
            self.stdout.write(self.style.SUCCESS("✅ Token saved successfully"))
            self.stdout.write(f"Token ID: {psn_token.id}")
            self.stdout.write(f"Expires at: {expires_at}")
            return True
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error saving token: {e}"))
            return False
    
    def test_trophy_data_fetching(self, access_token):
        """Test fetching trophy data with the access token"""
        self.stdout.write("🏆 Testing trophy data fetching...")
        
        # Test endpoints to try
        test_endpoints = [
            {
                "name": "Trophy Summary",
                "url": "https://m.np.playstation.com/api/trophy/v1/users/me/trophySummary",
                "description": "User's overall trophy statistics"
            },
            {
                "name": "Trophy Titles",
                "url": "https://m.np.playstation.com/api/trophy/v1/users/me/trophyTitles?limit=5",
                "description": "List of games with trophies"
            }
        ]
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        success_count = 0
        
        for endpoint in test_endpoints:
            try:
                self.stdout.write(f"\n📡 Testing {endpoint['name']}...")
                
                response = requests.get(endpoint['url'], headers=headers, timeout=10)
                
                # Log API call
                PSNApiCall.log_call(
                    call_type='trophy_summary' if 'Summary' in endpoint['name'] else 'game_list',
                    endpoint=endpoint['url'],
                    status='success' if response.status_code == 200 else 'error',
                    response_time_ms=int(response.elapsed.total_seconds() * 1000),
                    http_status=response.status_code,
                    response_size=len(response.content) if response.content else 0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.stdout.write(self.style.SUCCESS(f"✅ {endpoint['name']} - SUCCESS"))
                    
                    # Show some data details
                    if 'Summary' in endpoint['name']:
                        self.stdout.write(f"   Account ID: {data.get('accountId', 'Unknown')}")
                        self.stdout.write(f"   Trophy Level: {data.get('trophyLevel', 'Unknown')}")
                        earned = data.get('earnedTrophies', {})
                        self.stdout.write(f"   Trophies: 🥇{earned.get('platinum', 0)} 🥈{earned.get('gold', 0)} 🥉{earned.get('silver', 0)} 🏅{earned.get('bronze', 0)}")
                    
                    elif 'Titles' in endpoint['name']:
                        titles = data.get('trophyTitles', [])
                        self.stdout.write(f"   Found {len(titles)} games")
                        for i, title in enumerate(titles[:3]):  # Show first 3 games
                            self.stdout.write(f"   {i+1}. {title.get('trophyTitleName', 'Unknown')}")
                    
                    success_count += 1
                    
                else:
                    self.stdout.write(self.style.ERROR(f"❌ {endpoint['name']} - HTTP {response.status_code}"))
                    self.stdout.write(f"   Response: {response.text[:200]}")
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ {endpoint['name']} - Error: {e}"))
        
        if success_count == len(test_endpoints):
            self.stdout.write(self.style.SUCCESS(f"\n🎉 All {len(test_endpoints)} endpoints working perfectly!"))
            return True
        elif success_count > 0:
            self.stdout.write(self.style.WARNING(f"\n⚠️  {success_count}/{len(test_endpoints)} endpoints working"))
            return True
        else:
            self.stdout.write(self.style.ERROR(f"\n❌ No endpoints working"))
            return False
    
    def get_auth_code_only(self, npsso_token):
        """Get authorization code only (for step-by-step flow)"""
        code = self.get_auth_code(npsso_token)
        if code:
            self.stdout.write(self.style.SUCCESS(f"\n✅ Authorization code: {code}"))
            self.stdout.write("\nNext step:")
            self.stdout.write(f"python manage.py debug_psn_oauth --code {code}")
        return code
    
    def exchange_code_for_token(self, auth_code):
        """Exchange authorization code for access token (for step-by-step flow)"""
        token_data = self.get_access_token(auth_code)
        if token_data:
            saved = self.save_token_to_database(token_data)
            if saved:
                self.stdout.write(self.style.SUCCESS("\n✅ Token saved! Testing now..."))
                self.test_trophy_data_fetching(token_data['access_token'])
        return token_data
    
    def test_saved_token(self):
        """Test the most recent saved token"""
        try:
            # Get most recent active token
            token = PSNToken.objects.filter(active=True).order_by('-created_at').first()
            
            if not token:
                self.stdout.write(self.style.ERROR("❌ No active tokens found in database"))
                self.stdout.write("Run the full flow first: --full-flow --npsso YOUR_TOKEN")
                return False
            
            if token.is_expired():
                self.stdout.write(self.style.ERROR("❌ Token has expired"))
                self.stdout.write("Run the full flow again to get a new token")
                return False
            
            self.stdout.write(f"🔍 Testing token created at: {token.created_at}")
            return self.test_trophy_data_fetching(token.access_token)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error testing saved token: {e}"))
            return False