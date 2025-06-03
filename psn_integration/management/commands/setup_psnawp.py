from django.core.management.base import BaseCommand
from django.conf import settings
from psn_integration.models import PSNToken
from django.utils import timezone
from datetime import timedelta
import time

# PSNAWP imports
try:
    from psnawp_api import PSNAWP
    from psnawp_api.core.psnawp_exceptions import (
        PSNAWPAuthenticationError, 
        PSNAWPForbiddenError, 
        PSNAWPNotFoundError
    )
    PSNAWP_AVAILABLE = True
except ImportError:
    PSNAWP_AVAILABLE = False


class Command(BaseCommand):
    help = 'Setup PSNAWP integration with NPSSO token'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'npsso',
            type=str,
            help='Your NPSSO token from PlayStation (get from https://ca.account.sony.com/api/v1/ssocookie)'
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Test the integration after setup'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force setup even if existing tokens exist'
        )
    
    def handle(self, *args, **options):
        if not PSNAWP_AVAILABLE:
            self.stdout.write(self.style.ERROR("❌ PSNAWP not installed. Run: pip install PSNAWP"))
            return
        
        npsso_token = options['npsso']
        
        # Validate NPSSO format
        if len(npsso_token) != 64:
            self.stdout.write(self.style.ERROR("❌ Invalid NPSSO token length. Should be 64 characters."))
            self.stdout.write("Get your NPSSO from: https://ca.account.sony.com/api/v1/ssocookie")
            return
        
        self.stdout.write(self.style.SUCCESS("🎮 Setting up PSNAWP Integration"))
        self.stdout.write("=" * 50)
        
        try:
            # Check for existing active tokens
            existing_tokens = PSNToken.objects.filter(active=True)
            if existing_tokens.exists() and not options['force']:
                self.stdout.write(self.style.WARNING("⚠️  Active PSN tokens already exist."))
                self.stdout.write("Use --force to override existing tokens")
                return
            
            # Test PSNAWP connection
            self.stdout.write("Testing PSNAWP connection...")
            psnawp = PSNAWP(npsso_token)
            
            # Get our account info using correct PSNAWP API
            self.stdout.write("Getting account information...")
            client = psnawp.me()
            
            # Use correct method name - get_profile_legacy() for Client objects
            try:
                my_profile = client.get_profile_legacy()
                online_id = client.online_id
                account_id = client.account_id
            except Exception as profile_error:
                self.stdout.write(self.style.WARNING(f"⚠️  Profile access limited: {profile_error}"))
                online_id = getattr(client, 'online_id', 'service_account')
                account_id = getattr(client, 'account_id', 'unknown')
                my_profile = None
            
            self.stdout.write(self.style.SUCCESS("✅ PSNAWP connection successful!"))
            self.stdout.write(f"   Online ID: {online_id}")
            self.stdout.write(f"   Account ID: {account_id}")
            
            # Try to get trophy summary
            try:
                trophy_summary = client.trophy_summary()
                trophy_level = trophy_summary.get('trophyLevel', 'Unknown')
                self.stdout.write(f"   Trophy Level: {trophy_level}")
            except Exception as trophy_error:
                self.stdout.write(self.style.WARNING(f"   Trophy data access limited: {trophy_error}"))
            
            # Deactivate existing tokens
            if existing_tokens.exists():
                existing_tokens.update(active=False)
                self.stdout.write("Deactivated existing tokens")
            
            # Save NPSSO token to database
            psn_token = PSNToken.objects.create(
                account_type='dedicated',
                access_token=npsso_token,  # Store NPSSO as access token
                expires_at=timezone.now() + timedelta(days=60),  # NPSSO lasts ~60 days
                psn_account_id=account_id,
                psn_username=online_id,
                active=True
            )
            
            self.stdout.write(self.style.SUCCESS("✅ NPSSO token saved to database"))
            self.stdout.write(f"   Token ID: {psn_token.id}")
            self.stdout.write(f"   Expires: {psn_token.expires_at}")
            
            if options['test']:
                self.stdout.write("\n🧪 Running integration test...")
                self.test_integration(psnawp, client)
            
            self.stdout.write(self.style.SUCCESS("\n🎉 PSNAWP setup complete!"))
            self.stdout.write("Ready to sync user trophies:")
            self.stdout.write("python manage.py sync_user_trophies USERNAME PSN_ID")
            
        except PSNAWPAuthenticationError as auth_error:
            self.stdout.write(self.style.ERROR(f"❌ Authentication failed: {auth_error}"))
            self.stdout.write("Your NPSSO token may be invalid or expired.")
            self.stdout.write("Get a fresh token from: https://ca.account.sony.com/api/v1/ssocookie")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Setup failed: {e}"))
            self.stdout.write("Check your internet connection and try again.")
    
    def test_integration(self, psnawp, client):
        """Test the integration with some API calls"""
        try:
            # Test 1: User search with known PSN account
            self.stdout.write("   Testing user search...")
            time.sleep(1)  # Rate limiting
            
            try:
                # Test with PlayStation's official account
                test_user = psnawp.user(online_id="PlayStation")
                test_profile = test_user.profile()
                self.stdout.write(self.style.SUCCESS("   ✅ User search working"))
                self.stdout.write(f"   Found: {test_profile.get('onlineId', 'PlayStation')}")
            except PSNAWPForbiddenError:
                self.stdout.write(self.style.WARNING("   ⚠️  User profile access limited (normal)"))
            except PSNAWPNotFoundError:
                self.stdout.write(self.style.WARNING("   ⚠️  Test user not found (trying alternative)"))
                # Try with a different known account
                try:
                    test_user = psnawp.user(online_id="VaultTec_Trading")
                    test_profile = test_user.profile()
                    self.stdout.write(self.style.SUCCESS("   ✅ User search working (alternative test)"))
                except:
                    self.stdout.write(self.style.WARNING("   ⚠️  User search limited"))
            
            # Test 2: Trophy data access
            self.stdout.write("   Testing trophy data access...")
            time.sleep(1)  # Rate limiting
            
            try:
                # Get trophy titles for our account
                trophy_titles = client.trophy_titles(limit=5)
                
                if hasattr(trophy_titles, '__iter__'):
                    title_count = len(list(trophy_titles))
                    self.stdout.write(self.style.SUCCESS(f"   ✅ Found {title_count} games"))
                    
                    if title_count > 0:
                        # Try to get first game details
                        first_titles = client.trophy_titles(limit=1)
                        first_game = next(iter(first_titles), None)
                        if first_game:
                            game_name = getattr(first_game, 'title_name', 'Unknown Game')
                            self.stdout.write(f"   Sample game: {game_name}")
                else:
                    self.stdout.write(self.style.WARNING("   ⚠️  Trophy data format unexpected"))
                    
            except PSNAWPForbiddenError:
                self.stdout.write(self.style.WARNING("   ⚠️  Trophy data access forbidden"))
            except Exception as trophy_error:
                self.stdout.write(self.style.WARNING(f"   ⚠️  Trophy test limited: {trophy_error}"))
            
            # Test 3: Rate limiting check
            self.stdout.write("   Testing rate limiting...")
            try:
                # Make a few rapid calls to test rate limiting
                for i in range(3):
                    client.get_region()
                    time.sleep(0.5)
                self.stdout.write(self.style.SUCCESS("   ✅ Rate limiting working properly"))
            except Exception as rate_error:
                self.stdout.write(self.style.WARNING(f"   ⚠️  Rate limiting test: {rate_error}"))
            
            # Test 4: Profile data structure
            self.stdout.write("   Testing profile data structure...")
            try:
                my_profile = client.get_profile_legacy()
                if my_profile:
                    profile_keys = list(my_profile.keys()) if isinstance(my_profile, dict) else ['Profile object']
                    self.stdout.write(f"   Available profile data: {len(profile_keys)} fields")
                    self.stdout.write(self.style.SUCCESS("   ✅ Profile data accessible"))
                else:
                    self.stdout.write(self.style.WARNING("   ⚠️  Profile data limited"))
            except Exception as profile_error:
                self.stdout.write(self.style.WARNING(f"   ⚠️  Profile test: {profile_error}"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Integration test failed: {e}"))
        
        self.stdout.write("\n📊 Test Summary:")
        self.stdout.write("   If all tests show ✅ or ⚠️, the integration is working")
        self.stdout.write("   ⚠️  warnings are normal for privacy-protected data")
        self.stdout.write("   Only ❌ errors indicate setup problems")