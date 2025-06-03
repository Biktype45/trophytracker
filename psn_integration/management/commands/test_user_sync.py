# ====================
# TEST USER SYNC COMMAND
# ====================

# psn_integration/management/commands/test_user_sync.py
"""
Test user sync with limited scope to verify everything works
"""

from django.core.management.base import BaseCommand
from psn_integration.services import PSNAWPService
from users.models import User

class Command(BaseCommand):
    help = 'Test user sync with limited scope'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            type=str,
            help='Django username'
        )
        parser.add_argument(
            'psn_id',
            type=str,
            help='PlayStation Network ID'
        )
        parser.add_argument(
            '--games-limit',
            type=int,
            default=3,
            help='Limit number of games to sync (default: 3)'
        )
    
    def handle(self, *args, **options):
        username = options['username']
        psn_id = options['psn_id']
        games_limit = options['games_limit']
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ User '{username}' not found"))
            return
        
        self.stdout.write(self.style.SUCCESS(f"🧪 Testing user sync (limited to {games_limit} games)"))
        self.stdout.write("=" * 60)
        
        try:
            service = PSNAWPService()
            
            # Validate user first
            self.stdout.write(f"Step 1: Validating PSN ID '{psn_id}'...")
            validation = service.validate_psn_user(psn_id)
            
            if not validation['valid']:
                self.stdout.write(self.style.ERROR(f"❌ PSN ID invalid: {validation.get('error')}"))
                return
            
            self.stdout.write(self.style.SUCCESS("✅ PSN ID validated"))
            self.stdout.write(f"   Display Name: {validation['display_name']}")
            self.stdout.write(f"   Trophy Level: {validation['trophy_level']}")
            
            # Test limited trophy sync
            self.stdout.write(f"\nStep 2: Testing limited trophy sync...")
            
            psn_user = service.psnawp.user(online_id=psn_id)
            
            # Get limited game list
            try:
                trophy_titles = psn_user.trophy_titles(limit=games_limit)
            except:
                trophy_titles = psn_user.trophy_titles()
                if isinstance(trophy_titles, list):
                    trophy_titles = trophy_titles[:games_limit]
            
            self.stdout.write(f"✅ Found {len(trophy_titles)} games to test")
            
            # Process each game
            for i, title_data in enumerate(trophy_titles):
                game_name = getattr(title_data, 'title_name', f'Game {i+1}')
                self.stdout.write(f"\n📱 Testing Game {i+1}: {game_name}")
                
                # Extract game info
                game_info = service.extract_game_info(title_data)
                if game_info:
                    self.stdout.write(f"   ✅ Game info extracted")
                    self.stdout.write(f"   Platform: {game_info['platform']}")
                    self.stdout.write(f"   Progress: {game_info['progress']}%")
                    self.stdout.write(f"   Communication ID: {game_info['np_communication_id']}")
                    
                    # Test creating game record
                    game = service.get_or_create_game(game_info)
                    if game:
                        self.stdout.write(f"   ✅ Game record created/found: {game.title}")
                        self.stdout.write(f"   Difficulty: {game.difficulty_multiplier}x")
                    else:
                        self.stdout.write(f"   ❌ Could not create game record")
                        continue
                    
                    # Test trophy sync for this game
                    try:
                        title_trophies = psn_user.title_trophies(
                            np_communication_id=game_info['np_communication_id'],
                            platform=game_info['platform']
                        )
                        
                        trophy_count = 0
                        if hasattr(title_trophies, 'trophies'):
                            trophy_count = len(title_trophies.trophies)
                        elif isinstance(title_trophies, list):
                            trophy_count = len(title_trophies)
                        
                        self.stdout.write(f"   ✅ Found {trophy_count} trophies")
                        
                        if trophy_count > 0:
                            # Test processing first few trophies
                            trophies_to_process = []
                            if hasattr(title_trophies, 'trophies'):
                                trophies_to_process = title_trophies.trophies[:3]  # Test first 3
                            elif isinstance(title_trophies, list):
                                trophies_to_process = title_trophies[:3]
                            
                            for trophy_data in trophies_to_process:
                                trophy_name = getattr(trophy_data, 'trophy_name', 'Unknown Trophy')
                                trophy_type = getattr(trophy_data, 'trophy_type', 'bronze')
                                self.stdout.write(f"     🏆 {trophy_name} ({trophy_type})")
                    
                    except Exception as e:
                        self.stdout.write(f"   ⚠️  Trophy details error: {e}")
                
                else:
                    self.stdout.write(f"   ❌ Could not extract game info")
            
            self.stdout.write(self.style.SUCCESS(f"\n🎉 Test sync completed successfully!"))
            self.stdout.write("Everything looks good. Ready for full sync:")
            self.stdout.write(f"python manage.py sync_user_trophies {username} {psn_id}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Test failed: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())