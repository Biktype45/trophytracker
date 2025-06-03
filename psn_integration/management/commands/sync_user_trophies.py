from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from psn_integration.models import PSNToken, PSNSyncJob, PSNUserValidation
from games.models import Game
from trophies.models import Trophy, UserTrophy, UserGameProgress
from users.models import User
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
    help = 'Sync PlayStation trophies for a user and calculate skill-based scores'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            type=str,
            help='Django username to sync trophies for'
        )
        parser.add_argument(
            'psn_id',
            type=str,
            help='PlayStation Network ID to sync from'
        )
        parser.add_argument(
            '--create-user',
            action='store_true',
            help='Create Django user if it doesn\'t exist'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Limit number of games to sync (default: 10, use 0 for all)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without saving to database'
        )
    
    def handle(self, *args, **options):
        if not PSNAWP_AVAILABLE:
            self.stdout.write(self.style.ERROR("❌ PSNAWP not installed. Run: pip install PSNAWP"))
            return
        
        username = options['username']
        psn_id = options['psn_id']
        limit = options['limit'] if options['limit'] > 0 else None
        
        self.stdout.write(self.style.SUCCESS(f"🎮 Syncing PSN Profile: {psn_id} → {username}"))
        self.stdout.write("=" * 60)
        
        try:
            # Get active PSN token
            psn_token = PSNToken.objects.filter(active=True).first()
            if not psn_token:
                self.stdout.write(self.style.ERROR("❌ No active PSN token found. Run setup_psnawp first."))
                return
            
            if psn_token.is_expired():
                self.stdout.write(self.style.ERROR("❌ PSN token has expired. Run setup_psnawp again."))
                return
            
            # Get or create Django user
            try:
                user = User.objects.get(username=username)
                self.stdout.write(f"✅ Found user: {user.username}")
            except User.DoesNotExist:
                if options['create_user']:
                    user = User.objects.create_user(
                        username=username,
                        psn_id=psn_id
                    )
                    self.stdout.write(self.style.SUCCESS(f"✅ Created new user: {username}"))
                else:
                    self.stdout.write(self.style.ERROR(f"❌ User '{username}' not found. Use --create-user to create."))
                    return
            
            # Store pre-sync stats
            score_before = user.total_trophy_score
            level_before = user.current_trophy_level
            
            # Create sync job
            sync_job = PSNSyncJob.objects.create(
                user=user,
                sync_type='manual',
                score_before=score_before,
                level_before=level_before
            )
            sync_job.mark_started()
            
            # Initialize PSNAWP
            self.stdout.write("Initializing PlayStation API...")
            psnawp = PSNAWP(psn_token.access_token)
            
            # Validate and get PSN user
            self.stdout.write(f"Validating PSN ID: {psn_id}")
            psn_user_data = self.validate_psn_user(psnawp, psn_id, sync_job)
            if not psn_user_data:
                sync_job.mark_completed(success=False)
                return
            
            # Update user with PSN data
            if not options['dry_run']:
                user.psn_id = psn_id
                user.psn_account_id = psn_user_data.get('account_id')
                user.psn_avatar_url = psn_user_data.get('avatar_url', '')
                user.save()
            
            # Sync trophy data
            self.stdout.write(f"\n🏆 Fetching trophy data for {psn_id}...")
            self.sync_trophy_data(psnawp, user, psn_id, sync_job, limit, options['dry_run'])
            
            if not options['dry_run']:
                # Recalculate user scores
                self.stdout.write("\n📊 Calculating skill-based scores...")
                user.calculate_total_score()
                user.update_trophy_level()
                
                # Update sync job results
                sync_job.score_after = user.total_trophy_score
                sync_job.level_after = user.current_trophy_level
                sync_job.mark_completed(success=True)
                
                # Display results
                self.display_sync_results(user, score_before, level_before, sync_job)
            else:
                self.stdout.write(self.style.WARNING("\n🔍 DRY RUN - No changes saved to database"))
                sync_job.delete()  # Remove dry run job
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Sync failed: {e}"))
            if 'sync_job' in locals():
                sync_job.error_message = str(e)
                sync_job.mark_completed(success=False)
    
    def validate_psn_user(self, psnawp, psn_id, sync_job):
        """Validate PSN user and get basic profile info"""
        try:
            psn_user = psnawp.user(online_id=psn_id)
            
            # Try to get profile data
            try:
                profile = psn_user.profile()
                is_public = True
                self.stdout.write(self.style.SUCCESS(f"✅ PSN profile found: {psn_id}"))
            except PSNAWPForbiddenError:
                self.stdout.write(self.style.WARNING(f"⚠️  PSN profile is private: {psn_id}"))
                is_public = False
                profile = {'onlineId': psn_id}
            
            # Try to get legacy profile for more data
            try:
                legacy_profile = psn_user.get_profile_legacy()
                if legacy_profile:
                    profile.update(legacy_profile)
            except:
                pass
            
            # Cache validation result
            PSNUserValidation.objects.update_or_create(
                psn_id=psn_id,
                defaults={
                    'validation_status': 'valid' if is_public else 'private',
                    'is_valid': True,
                    'is_public': is_public,
                    'psn_account_id': getattr(psn_user, 'account_id', ''),
                    'display_name': profile.get('onlineId', psn_id),
                    'avatar_url': profile.get('avatarUrls', {}).get('size_l', '') if isinstance(profile.get('avatarUrls'), dict) else ''
                }
            )
            
            return {
                'account_id': getattr(psn_user, 'account_id', ''),
                'online_id': profile.get('onlineId', psn_id),
                'avatar_url': profile.get('avatarUrls', {}).get('size_l', '') if isinstance(profile.get('avatarUrls'), dict) else '',
                'is_public': is_public,
                'psn_user': psn_user
            }
            
        except PSNAWPNotFoundError:
            self.stdout.write(self.style.ERROR(f"❌ PSN ID not found: {psn_id}"))
            PSNUserValidation.objects.update_or_create(
                psn_id=psn_id,
                defaults={
                    'validation_status': 'not_found',
                    'is_valid': False,
                    'last_error': 'PSN ID not found'
                }
            )
            return None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ PSN validation error: {e}"))
            return None
    
    def sync_trophy_data(self, psnawp, user, psn_id, sync_job, limit, dry_run):
        """Sync trophy data for the user"""
        try:
            psn_user = psnawp.user(online_id=psn_id)
            
            # Get trophy titles (games)
            self.stdout.write("Fetching game list...")
            trophy_titles = psn_user.trophy_titles(limit=limit)
            
            games_processed = 0
            trophies_synced = 0
            new_games = 0
            
            for title in trophy_titles:
                games_processed += 1
                
                # Update progress
                progress = int((games_processed / (limit or 50)) * 100)
                sync_job.update_progress(progress, f"Processing game {games_processed}")
                
                self.stdout.write(f"\n📀 Game {games_processed}: {title.title_name}")
                self.stdout.write(f"   Platform: {getattr(title, 'title_platform', 'Unknown')}")
                
                # Get or create game
                game = self.get_or_create_game(title, dry_run)
                if not game:
                    continue
                
                if not dry_run and not Game.objects.filter(np_communication_id=title.np_communication_id).exists():
                    new_games += 1
                
                # Get trophy data for this game
                game_trophies = self.sync_game_trophies(psnawp, psn_user, user, game, title, dry_run)
                trophies_synced += game_trophies
                
                # Rate limiting
                time.sleep(1)
            
            sync_job.games_found = games_processed
            sync_job.games_created = new_games
            sync_job.trophies_synced = trophies_synced
            sync_job.save()
            
        except PSNAWPForbiddenError:
            self.stdout.write(self.style.ERROR(f"❌ Trophy data access forbidden for {psn_id}"))
            sync_job.error_message = "Trophy data is private"
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Trophy sync error: {e}"))
            sync_job.error_message = str(e)
    
    def get_or_create_game(self, title, dry_run):
        """Get or create a game from PSN title data"""
        try:
            np_comm_id = title.np_communication_id
            
            # Extract trophy counts safely from PSNAWP data structure
            trophy_counts = self.extract_trophy_counts(title)
            
            if dry_run:
                # For dry run, check if game exists
                existing = Game.objects.filter(np_communication_id=np_comm_id).first()
                if existing:
                    self.stdout.write(f"   🎮 Existing game: {existing.title} (Multiplier: {existing.difficulty_multiplier}x)")
                    return existing
                else:
                    multiplier = self.suggest_difficulty_multiplier(title.title_name)
                    self.stdout.write(f"   🆕 Would create new game: {title.title_name} ({multiplier}x)")
                    # Create a temporary game object for dry run calculations
                    return Game(
                        np_communication_id=np_comm_id,
                        title=title.title_name,
                        platform=getattr(title, 'title_platform', 'PS5'),
                        difficulty_multiplier=multiplier,
                        **trophy_counts
                    )
            
            # Try to get existing game
            game, created = Game.objects.get_or_create(
                np_communication_id=np_comm_id,
                defaults={
                    'title': title.title_name,
                    'platform': getattr(title, 'title_platform', 'PS5'),
                    'difficulty_multiplier': self.suggest_difficulty_multiplier(title.title_name),
                    **trophy_counts
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f"   🆕 Created new game: {game.title} ({game.difficulty_multiplier}x)"))
                # Display trophy breakdown
                total = sum(trophy_counts.values())
                self.stdout.write(f"      Trophies: {total} total ({trophy_counts['bronze_count']}🥉 {trophy_counts['silver_count']}🥈 {trophy_counts['gold_count']}🥇 {trophy_counts['platinum_count']}🏆)")
            else:
                self.stdout.write(f"   🎮 Found existing game: {game.title} ({game.difficulty_multiplier}x)")
            
            return game
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Game creation error: {e}"))
            # Print debug info to help troubleshoot
            self.stdout.write(f"   Debug - Title object type: {type(title)}")
            self.stdout.write(f"   Debug - Available attributes: {[attr for attr in dir(title) if not attr.startswith('_')]}")
            return None
    
    def extract_trophy_counts(self, title):
        """Extract trophy counts from PSNAWP title object safely"""
        trophy_counts = {
            'bronze_count': 0,
            'silver_count': 0,
            'gold_count': 0,
            'platinum_count': 0
        }
        
        try:
            # Try different possible attribute names for trophy data
            defined_trophies = None
            
            # Check for defined_trophies attribute (most common)
            if hasattr(title, 'defined_trophies'):
                defined_trophies = title.defined_trophies
            
            # Check for trophies attribute
            elif hasattr(title, 'trophies'):
                defined_trophies = title.trophies
            
            # Check for trophy_counts attribute
            elif hasattr(title, 'trophy_counts'):
                defined_trophies = title.trophy_counts
            
            if defined_trophies:
                # Handle if it's a dict-like object
                if hasattr(defined_trophies, 'get'):
                    trophy_counts['bronze_count'] = defined_trophies.get('bronze', 0)
                    trophy_counts['silver_count'] = defined_trophies.get('silver', 0)
                    trophy_counts['gold_count'] = defined_trophies.get('gold', 0)
                    trophy_counts['platinum_count'] = defined_trophies.get('platinum', 0)
                
                # Handle if it's an object with attributes
                elif hasattr(defined_trophies, 'bronze'):
                    trophy_counts['bronze_count'] = getattr(defined_trophies, 'bronze', 0)
                    trophy_counts['silver_count'] = getattr(defined_trophies, 'silver', 0)
                    trophy_counts['gold_count'] = getattr(defined_trophies, 'gold', 0)
                    trophy_counts['platinum_count'] = getattr(defined_trophies, 'platinum', 0)
                
                # Handle if it's a list or other structure
                else:
                    self.stdout.write(f"   Debug - Trophy data structure: {type(defined_trophies)}: {defined_trophies}")
            
        except Exception as e:
            self.stdout.write(f"   ⚠️  Could not extract trophy counts: {e}")
        
        return trophy_counts
    
    def suggest_difficulty_multiplier(self, title):
        """Suggest difficulty multiplier based on game title"""
        title_lower = title.lower()
        
        # Easy publishers/patterns
        easy_patterns = ['ratalaika', 'sometimes you', 'eastasiasoft', 'pix arts']
        if any(pattern in title_lower for pattern in easy_patterns):
            return 1.0
        
        # Hard game patterns  
        souls_patterns = ['dark souls', 'bloodborne', 'sekiro', 'nioh', 'hollow knight']
        if any(pattern in title_lower for pattern in souls_patterns):
            return 6.0
        
        # Very hard patterns
        extreme_patterns = ['super meat boy', 'cuphead', 'celeste', 'crypt of the necrodancer']
        if any(pattern in title_lower for pattern in extreme_patterns):
            return 10.0
        
        # Default AAA standard
        return 3.0
    
    def sync_game_trophies(self, psnawp, psn_user, user, game, title, dry_run):
        """Sync trophies for a specific game"""
        try:
            # Get trophy data using the working PSNAWP pattern
            self.stdout.write(f"   Fetching trophy data for {title.np_communication_id}...")
            
            # Get the TrophySet (earned trophy counts)
            earned_trophy_set = getattr(title, 'earned_trophies', None)
            if not earned_trophy_set:
                self.stdout.write(f"   ⚠️  No earned trophy data available")
                return 0
            
            self.stdout.write(f"   Trophy data: {earned_trophy_set}")
            
            # Extract counts from TrophySet
            earned_counts = {
                'bronze': getattr(earned_trophy_set, 'bronze', 0),
                'silver': getattr(earned_trophy_set, 'silver', 0),
                'gold': getattr(earned_trophy_set, 'gold', 0),
                'platinum': getattr(earned_trophy_set, 'platinum', 0)
            }
            
            total_earned = sum(earned_counts.values())
            if total_earned == 0:
                self.stdout.write(f"   ⚠️  No trophies earned for this game")
                return 0
            
            self.stdout.write(f"   Earned: {earned_counts['bronze']}🥉 {earned_counts['silver']}🥈 {earned_counts['gold']}🥇 {earned_counts['platinum']}🏆")
            
            # Calculate scores for each trophy type
            trophies_processed = 0
            total_score = 0
            
            for trophy_type, count in earned_counts.items():
                if count > 0:
                    # Get base points for this trophy type
                    base_points = {'bronze': 1, 'silver': 3, 'gold': 6, 'platinum': 15}[trophy_type]
                    
                    # Calculate score for this trophy type
                    score_per_trophy = int(base_points * game.difficulty_multiplier)
                    total_type_score = score_per_trophy * count
                    total_score += total_type_score
                    
                    if dry_run:
                        # Show what would be scored
                        if count == 1:
                            self.stdout.write(f"     🏆 {trophy_type.title()}: {count} trophy (+{total_type_score} points)")
                        else:
                            self.stdout.write(f"     🏆 {trophy_type.title()}: {count} trophies (+{score_per_trophy} each = {total_type_score} points)")
                    else:
                        # For actual sync, we need to create placeholder trophies
                        # since we don't have individual trophy details from this API
                        for i in range(count):
                            # Create a unique integer trophy_id for each trophy type
                            # Use trophy type index + counter to ensure uniqueness
                            trophy_type_index = {'bronze': 1000, 'silver': 2000, 'gold': 3000, 'platinum': 4000}
                            trophy_id = trophy_type_index[trophy_type] + i
                            
                            trophy, created = Trophy.objects.get_or_create(
                                game=game,
                                trophy_id=trophy_id,  # Now using integer ID
                                defaults={
                                    'name': f'{trophy_type.title()} Trophy {i+1}',
                                    'description': f'Earned {trophy_type} trophy from {game.title}',
                                    'trophy_type': trophy_type,
                                    'hidden': False,
                                }
                            )
                            
                            # Create user trophy record
                            user_trophy, ut_created = UserTrophy.objects.get_or_create(
                                user=user,
                                trophy=trophy,
                                defaults={
                                    'earned': True,
                                    'earned_datetime': timezone.now()  # We don't have exact times
                                }
                            )
                            
                            trophies_processed += 1
                        
                        if count == 1:
                            self.stdout.write(f"     🏆 {trophy_type.title()}: {count} trophy (+{total_type_score} points)")
                        else:
                            self.stdout.write(f"     🏆 {trophy_type.title()}: {count} trophies (+{score_per_trophy} each = {total_type_score} points)")
            
            if dry_run:
                self.stdout.write(f"   ✅ Would process {total_earned} earned trophies for {total_score} total points")
            else:
                # Update user trophy counts for this game
                UserGameProgress.objects.update_or_create(
                    user=user,
                    game=game,
                    defaults={
                        'bronze_earned': earned_counts['bronze'],
                        'silver_earned': earned_counts['silver'],
                        'gold_earned': earned_counts['gold'],
                        'platinum_earned': earned_counts['platinum'],
                        'total_score_earned': total_score,
                        'last_trophy_date': timezone.now()
                    }
                )
                
                self.stdout.write(f"   ✅ Processed {total_earned} earned trophies for {total_score} total points")
            
            return total_earned
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Trophy sync error: {e}"))
            # Show debug info
            self.stdout.write(f"   Debug - Title type: {type(title)}")
            self.stdout.write(f"   Debug - Exception details: {str(e)}")
            if hasattr(title, 'earned_trophies'):
                self.stdout.write(f"   Debug - earned_trophies type: {type(title.earned_trophies)}")
                self.stdout.write(f"   Debug - earned_trophies value: {title.earned_trophies}")
            return 0
    
    def extract_trophy_info(self, trophy_data):
        """Extract trophy information from different PSNAWP trophy data structures"""
        try:
            trophy_info = {}
            
            # Handle if trophy_data is a dict
            if isinstance(trophy_data, dict):
                return trophy_data
            
            # Handle if trophy_data is an object with attributes
            elif hasattr(trophy_data, '__dict__'):
                # Try common attribute names
                trophy_info['trophy_id'] = getattr(trophy_data, 'trophy_id', getattr(trophy_data, 'id', 0))
                trophy_info['trophy_name'] = getattr(trophy_data, 'trophy_name', getattr(trophy_data, 'name', 'Unknown Trophy'))
                trophy_info['trophy_detail'] = getattr(trophy_data, 'trophy_detail', getattr(trophy_data, 'description', ''))
                trophy_info['trophy_type'] = getattr(trophy_data, 'trophy_type', getattr(trophy_data, 'type', 'bronze'))
                trophy_info['trophy_hidden'] = getattr(trophy_data, 'trophy_hidden', getattr(trophy_data, 'hidden', False))
                trophy_info['earned'] = getattr(trophy_data, 'earned', False)
                trophy_info['earned_date_time'] = getattr(trophy_data, 'earned_date_time', getattr(trophy_data, 'earned_datetime', None))
                
                return trophy_info
            
            else:
                # Unknown structure, try to log it for debugging
                self.stdout.write(f"   Debug - Unknown trophy data structure: {type(trophy_data)}")
                return None
                
        except Exception as e:
            self.stdout.write(f"   ⚠️  Could not extract trophy info: {e}")
            return None
    
    def display_sync_results(self, user, score_before, level_before, sync_job):
        """Display sync results"""
        self.stdout.write(self.style.SUCCESS("\n🎉 SYNC COMPLETE!"))
        self.stdout.write("=" * 50)
        self.stdout.write(f"User: {user.username} ({user.psn_id})")
        self.stdout.write(f"Games Found: {sync_job.games_found}")
        self.stdout.write(f"New Games Added: {sync_job.games_created}")
        self.stdout.write(f"Trophies Synced: {sync_job.trophies_synced}")
        self.stdout.write(f"Duration: {sync_job.duration_seconds():.1f} seconds")
        
        self.stdout.write("\n📊 SCORE CHANGES:")
        self.stdout.write(f"Score: {score_before:,} → {user.total_trophy_score:,} (+{sync_job.score_gained():,})")
        self.stdout.write(f"Level: {level_before} → {user.current_trophy_level} (+{sync_job.level_gained()})")
        self.stdout.write(f"Trophy Level: {user.get_trophy_level_name()}")
        self.stdout.write(f"Progress: {user.level_progress_percentage:.1f}%")
        
        if sync_job.score_gained() > 0:
            self.stdout.write(self.style.SUCCESS(f"\n🚀 Skill-based scoring is working! {sync_job.score_gained():,} points gained!"))
        
        self.stdout.write(f"\nNext steps:")
        self.stdout.write(f"• View profile: python manage.py shell -c \"from users.models import User; print(User.objects.get(username='{user.username}'))\"")
        self.stdout.write(f"• Check games: python manage.py shell -c \"from games.models import Game; print(Game.objects.count())\"")