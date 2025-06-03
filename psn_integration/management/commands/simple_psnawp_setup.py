# psn_integration/management/commands/simple_psnawp_setup.py
"""
Super simple PSNAWP setup that adapts to actual API structure
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from psn_integration.models import PSNToken
from datetime import timedelta

class Command(BaseCommand):
    help = 'Simple adaptive PSNAWP setup'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'npsso',
            type=str,
            help='Your NPSSO token from PlayStation'
        )
        parser.add_argument(
            '--test-only',
            action='store_true',
            help='Just test, don\'t save token'
        )
    
    def handle(self, *args, **options):
        npsso_token = options['npsso']
        
        self.stdout.write(self.style.SUCCESS("🎮 Simple PSNAWP Setup"))
        self.stdout.write("=" * 40)
        
        try:
            # Step 1: Test PSNAWP import
            self.stdout.write("Step 1: Testing PSNAWP import...")
            from psnawp_api import PSNAWP
            self.stdout.write(self.style.SUCCESS("✅ PSNAWP imported successfully"))
            
            # Step 2: Create client
            self.stdout.write("Step 2: Creating PSNAWP client...")
            psnawp = PSNAWP(npsso_token)
            self.stdout.write(self.style.SUCCESS("✅ PSNAWP client created"))
            
            # Step 3: Get me object
            self.stdout.write("Step 3: Getting account info...")
            me = psnawp.me()
            self.stdout.write(self.style.SUCCESS("✅ Account connection successful"))
            
            # Step 4: Test basic operations
            self.stdout.write("Step 4: Testing basic operations...")
            
            # Test profile
            try:
                profile = me.profile()
                self.stdout.write(self.style.SUCCESS("✅ Profile access works"))
                
                # Extract what we can
                online_id = "Unknown"
                if isinstance(profile, dict):
                    online_id = profile.get('onlineId', 'Unknown')
                else:
                    online_id = getattr(profile, 'online_id', 'Unknown')
                
                self.stdout.write(f"   Online ID: {online_id}")
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️  Profile access limited: {e}"))
            
            # Test trophy summary
            try:
                trophy_summary = me.trophy_summary()
                self.stdout.write(self.style.SUCCESS("✅ Trophy summary works"))
                
                # Extract trophy level
                trophy_level = 1
                if isinstance(trophy_summary, dict):
                    trophy_level = trophy_summary.get('trophyLevel', 1)
                else:
                    trophy_level = getattr(trophy_summary, 'trophy_level', 1)
                
                self.stdout.write(f"   Trophy Level: {trophy_level}")
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️  Trophy summary limited: {e}"))
            
            # Test trophy titles
            try:
                self.stdout.write("Step 5: Testing trophy titles...")
                
                # Try different ways to get trophy titles
                trophy_titles = None
                try:
                    trophy_titles = me.trophy_titles(limit=3)
                except:
                    try:
                        trophy_titles = me.trophy_titles()
                        if isinstance(trophy_titles, list) and len(trophy_titles) > 3:
                            trophy_titles = trophy_titles[:3]
                    except:
                        trophy_titles = []
                
                if trophy_titles and len(trophy_titles) > 0:
                    self.stdout.write(self.style.SUCCESS(f"✅ Found {len(trophy_titles)} games"))
                    
                    # Test first game
                    first_game = trophy_titles[0]
                    game_name = getattr(first_game, 'title_name', 'Unknown Game')
                    self.stdout.write(f"   Sample game: {game_name}")
                    
                    # Test trophy details for first game
                    try:
                        np_comm_id = getattr(first_game, 'np_communication_id', '')
                        platform = getattr(first_game, 'title_platform', 'PS4')
                        
                        if np_comm_id:
                            self.stdout.write("   Testing trophy details...")
                            game_trophies = me.title_trophies(
                                np_communication_id=np_comm_id,
                                platform=platform
                            )
                            
                            trophy_count = 0
                            if hasattr(game_trophies, 'trophies'):
                                trophy_count = len(game_trophies.trophies)
                            elif isinstance(game_trophies, list):
                                trophy_count = len(game_trophies)
                            
                            self.stdout.write(self.style.SUCCESS(f"   ✅ Found {trophy_count} trophies in {game_name}"))
                        
                    except Exception as e:
                        self.stdout.write(f"   ⚠️  Trophy details limited: {e}")
                
                else:
                    self.stdout.write(self.style.WARNING("⚠️  No games found or access limited"))
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️  Trophy titles limited: {e}"))
            
            # Step 6: Save token if test successful
            if not options['test_only']:
                self.stdout.write("Step 6: Saving token...")
                
                # Deactivate old tokens
                PSNToken.objects.filter(active=True).update(active=False)
                
                # Save new token
                PSNToken.objects.create(
                    account_type='dedicated',
                    access_token=npsso_token,  # Store NPSSO as access token
                    expires_at=timezone.now() + timedelta(days=60),
                    psn_username=online_id,
                    active=True
                )
                
                self.stdout.write(self.style.SUCCESS("✅ Token saved to database"))
            
            self.stdout.write(self.style.SUCCESS("\n🎉 PSNAWP setup successful!"))
            
            if not options['test_only']:
                self.stdout.write("\nNext steps:")
                self.stdout.write("1. Test user sync:")
                self.stdout.write("   python manage.py test_user_sync USERNAME PSN_ID")
                self.stdout.write("")
                self.stdout.write("2. Run full sync:")
                self.stdout.write("   python manage.py sync_user_trophies USERNAME PSN_ID")
            
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f"❌ PSNAWP not installed: {e}"))
            self.stdout.write("Run: pip install psnawp")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Setup failed: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())

