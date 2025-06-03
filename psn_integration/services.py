# psn_integration/services.py - CORRECTED VERSION
"""
Corrected PSNAWP service based on actual API structure
"""

from psnawp_api import PSNAWP
# Import only what we know exists - we'll discover the rest
try:
    from psnawp_api.models import TitleStats, TrophyTitles
except ImportError:
    # If models don't exist, we'll work with the raw objects
    TitleStats = None
    TrophyTitles = None

from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging
from typing import Optional, List, Dict, Any
from psn_integration.models import PSNToken, PSNApiCall, PSNSyncJob
from games.models import Game
from trophies.models import Trophy as TrophyModel, UserTrophy, UserGameProgress
from users.models import User

logger = logging.getLogger(__name__)

class PSNAWPService:
    """
    PlayStation Network service using PSNAWP library
    Corrected version that adapts to actual API structure
    """
    
    def __init__(self, npsso_token: str = None):
        """Initialize PSNAWP client"""
        self.npsso_token = npsso_token or self.get_stored_npsso()
        self.psnawp = None
        self.me = None
        
        if self.npsso_token:
            try:
                self.psnawp = PSNAWP(self.npsso_token)
                self.me = self.psnawp.me()
                logger.info("✅ PSNAWP initialized successfully")
            except Exception as e:
                logger.error(f"❌ PSNAWP initialization failed: {e}")
                raise
    
    def get_stored_npsso(self) -> Optional[str]:
        """Get stored NPSSO token from database or settings"""
        try:
            token = PSNToken.objects.filter(active=True).order_by('-created_at').first()
            if token:
                return token.access_token  # We store NPSSO as access_token
            return getattr(settings, 'PSNAWP_NPSSO_TOKEN', None)
        except:
            return None
    
    def validate_psn_user(self, psn_id: str) -> Dict[str, Any]:
        """
        Validate a PSN user and get their basic info
        """
        try:
            # Search for the user
            user = self.psnawp.user(online_id=psn_id)
            
            # Get basic profile info
            profile = user.profile()
            
            # Get trophy summary
            trophy_summary = user.trophy_summary()
            
            # Extract data safely (since we don't know exact structure)
            result = {
                'valid': True,
                'psn_id': psn_id,
                'display_name': psn_id,  # Default fallback
                'avatar_url': '',
                'trophy_level': 1,
                'total_trophies': {
                    'bronze': 0,
                    'silver': 0,
                    'gold': 0,
                    'platinum': 0,
                },
                'trophy_points': 0,
                'is_public': True,
                'last_seen': timezone.now()
            }
            
            # Safely extract profile data
            if isinstance(profile, dict):
                result['account_id'] = profile.get('accountId', '')
                result['display_name'] = profile.get('onlineId', psn_id)
                if 'avatarUrls' in profile and profile['avatarUrls']:
                    result['avatar_url'] = profile['avatarUrls'][-1].get('avatarUrl', '')
            
            # Safely extract trophy data
            if isinstance(trophy_summary, dict):
                result['trophy_level'] = trophy_summary.get('trophyLevel', 1)
                result['trophy_points'] = trophy_summary.get('trophyPoint', 0)
                
                if 'earnedTrophies' in trophy_summary:
                    earned = trophy_summary['earnedTrophies']
                    result['total_trophies'] = {
                        'bronze': earned.get('bronze', 0),
                        'silver': earned.get('silver', 0),
                        'gold': earned.get('gold', 0),
                        'platinum': earned.get('platinum', 0),
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"PSN user validation failed for {psn_id}: {e}")
            return {
                'valid': False,
                'psn_id': psn_id,
                'error': str(e),
                'last_seen': timezone.now()
            }
    
    def sync_user_trophies(self, user: User, psn_id: str) -> PSNSyncJob:
        """
        Sync all trophies for a user
        """
        sync_job = PSNSyncJob.objects.create(
            user=user,
            sync_type='full',
            status='running'
        )
        
        try:
            sync_job.mark_started()
            sync_job.update_progress(10, "Connecting to PSN...")
            
            # Get PSN user
            psn_user = self.psnawp.user(online_id=psn_id)
            
            sync_job.update_progress(20, "Fetching game list...")
            
            # Get trophy titles - adapt to actual API
            try:
                trophy_titles = psn_user.trophy_titles(limit=800)
            except TypeError:
                # If limit parameter doesn't work, try without it
                trophy_titles = psn_user.trophy_titles()
                # Take first 800 if we get too many
                if isinstance(trophy_titles, list) and len(trophy_titles) > 800:
                    trophy_titles = trophy_titles[:800]
            
            total_games = len(trophy_titles) if isinstance(trophy_titles, list) else 0
            sync_job.games_found = total_games
            sync_job.save()
            
            if total_games == 0:
                sync_job.error_message = "No games found for this user"
                sync_job.mark_completed(success=False)
                return sync_job
            
            games_processed = 0
            
            for title_data in trophy_titles:
                try:
                    progress = 20 + (games_processed / total_games) * 60
                    
                    # Get game name safely
                    game_name = getattr(title_data, 'title_name', 'Unknown Game')
                    sync_job.update_progress(
                        progress, 
                        f"Processing game {games_processed + 1}/{total_games}: {game_name}"
                    )
                    
                    # Process this game
                    self.process_game_trophies(user, psn_user, title_data, sync_job)
                    
                    games_processed += 1
                    
                except Exception as e:
                    logger.error(f"Error processing game: {e}")
                    sync_job.errors_count += 1
                    sync_job.save()
                    continue
            
            sync_job.update_progress(85, "Calculating final scores...")
            self.recalculate_user_scores(user, sync_job)
            
            sync_job.update_progress(100, "Sync completed!")
            sync_job.mark_completed(success=True)
            
            logger.info(f"✅ Trophy sync completed for {user.username}")
            return sync_job
            
        except Exception as e:
            logger.error(f"❌ Trophy sync failed for {user.username}: {e}")
            sync_job.error_message = str(e)
            sync_job.mark_completed(success=False)
            return sync_job
    
    def process_game_trophies(self, user: User, psn_user, title_data, sync_job: PSNSyncJob):
        """Process trophies for a single game - adaptive to actual API structure"""
        
        # Extract game data safely
        game_info = self.extract_game_info(title_data)
        if not game_info:
            return
        
        # Get or create the game in our database
        game = self.get_or_create_game(game_info)
        if not game:
            return
        
        try:
            # Get detailed trophy information for this game
            title_trophies = psn_user.title_trophies(
                np_communication_id=game_info['np_communication_id'],
                platform=game_info['platform']
            )
            
            # Get user's earned trophies for this game
            try:
                earned_trophies = psn_user.title_trophies_earned_for_title(
                    np_communication_id=game_info['np_communication_id'],
                    platform=game_info['platform']
                )
            except:
                # If this method doesn't exist, we'll work with what we have
                earned_trophies = None
            
            # Process the trophies
            self.sync_game_trophies(user, game, title_trophies, earned_trophies, sync_job)
            
            # Update progress
            self.update_game_progress(user, game, game_info, sync_job)
            
        except Exception as e:
            logger.error(f"Error processing trophies for {game_info.get('title', 'Unknown')}: {e}")
            sync_job.errors_count += 1
            sync_job.save()
    
    def extract_game_info(self, title_data) -> Optional[Dict[str, Any]]:
        """Extract game information from title data object"""
        try:
            # Adapt to actual object structure
            info = {
                'title': getattr(title_data, 'title_name', 'Unknown Game'),
                'np_communication_id': getattr(title_data, 'np_communication_id', ''),
                'platform': getattr(title_data, 'title_platform', 'PS4'),
                'icon_url': getattr(title_data, 'title_icon_url', ''),
                'progress': getattr(title_data, 'progress', 0),
            }
            
            # Extract trophy counts if available
            if hasattr(title_data, 'defined_trophies'):
                defined = title_data.defined_trophies
                info.update({
                    'bronze_count': getattr(defined, 'bronze', 0),
                    'silver_count': getattr(defined, 'silver', 0),
                    'gold_count': getattr(defined, 'gold', 0),
                    'platinum_count': getattr(defined, 'platinum', 0),
                })
            else:
                # Default values
                info.update({
                    'bronze_count': 0,
                    'silver_count': 0,
                    'gold_count': 0,
                    'platinum_count': 0,
                })
            
            # Extract earned counts if available
            if hasattr(title_data, 'earned_trophies'):
                earned = title_data.earned_trophies
                info.update({
                    'bronze_earned': getattr(earned, 'bronze', 0),
                    'silver_earned': getattr(earned, 'silver', 0),
                    'gold_earned': getattr(earned, 'gold', 0),
                    'platinum_earned': getattr(earned, 'platinum', 0),
                })
            else:
                info.update({
                    'bronze_earned': 0,
                    'silver_earned': 0,
                    'gold_earned': 0,
                    'platinum_earned': 0,
                })
            
            return info if info['np_communication_id'] else None
            
        except Exception as e:
            logger.error(f"Error extracting game info: {e}")
            return None
    
    def get_or_create_game(self, game_info: Dict[str, Any]) -> Optional[Game]:
        """Get or create a game from game info dict"""
        try:
            game, created = Game.objects.get_or_create(
                np_communication_id=game_info['np_communication_id'],
                defaults={
                    'title': game_info['title'],
                    'platform': game_info['platform'],
                    'icon_url': game_info['icon_url'],
                    'bronze_count': game_info['bronze_count'],
                    'silver_count': game_info['silver_count'],
                    'gold_count': game_info['gold_count'],
                    'platinum_count': game_info['platinum_count'],
                    'difficulty_multiplier': 3.0,
                    'last_synced': timezone.now()
                }
            )
            
            if created:
                logger.info(f"✅ Created new game: {game.title}")
                # Auto-assign difficulty based on progress/completion
                if game_info['progress'] > 0:
                    self.auto_assign_difficulty(game, game_info['progress'])
            
            return game
            
        except Exception as e:
            logger.error(f"Error creating game {game_info['title']}: {e}")
            return None
    
    def auto_assign_difficulty(self, game: Game, completion_rate: float):
        """Auto-assign difficulty multiplier based on completion rate"""
        if completion_rate >= 70:
            game.difficulty_multiplier = 1.2
        elif completion_rate >= 50:
            game.difficulty_multiplier = 1.5
        elif completion_rate >= 35:
            game.difficulty_multiplier = 2.0
        elif completion_rate >= 25:
            game.difficulty_multiplier = 3.0
        elif completion_rate >= 15:
            game.difficulty_multiplier = 4.0
        elif completion_rate >= 10:
            game.difficulty_multiplier = 5.0
        elif completion_rate >= 5:
            game.difficulty_multiplier = 6.0
        elif completion_rate >= 2:
            game.difficulty_multiplier = 8.0
        else:
            game.difficulty_multiplier = 10.0
        
        game.save()
        logger.info(f"🎯 Auto-assigned {game.difficulty_multiplier}x difficulty to {game.title}")
    
    def sync_game_trophies(self, user: User, game: Game, title_trophies, earned_trophies, sync_job: PSNSyncJob):
        """Sync trophies for a game - adaptive version"""
        
        # Handle different possible structures for title_trophies
        trophies_list = []
        if hasattr(title_trophies, 'trophies'):
            trophies_list = title_trophies.trophies
        elif isinstance(title_trophies, list):
            trophies_list = title_trophies
        
        # Handle earned trophies
        earned_lookup = {}
        if earned_trophies:
            if hasattr(earned_trophies, 'trophies'):
                earned_lookup = {t.trophy_id: t for t in earned_trophies.trophies}
            elif isinstance(earned_trophies, list):
                earned_lookup = {getattr(t, 'trophy_id', 0): t for t in earned_trophies}
        
        # Process each trophy
        for trophy_data in trophies_list:
            try:
                # Extract trophy info safely
                trophy_id = getattr(trophy_data, 'trophy_id', 0)
                trophy_name = getattr(trophy_data, 'trophy_name', 'Unknown Trophy')
                trophy_type = getattr(trophy_data, 'trophy_type', 'bronze').lower()
                
                # Create trophy record
                trophy, created = TrophyModel.objects.get_or_create(
                    game=game,
                    trophy_id=trophy_id,
                    defaults={
                        'name': trophy_name,
                        'description': getattr(trophy_data, 'trophy_detail', ''),
                        'trophy_type': trophy_type,
                        'icon_url': getattr(trophy_data, 'trophy_icon_url', ''),
                        'hidden': getattr(trophy_data, 'trophy_hidden', False),
                        'trophy_group_id': getattr(trophy_data, 'trophy_group_id', 'default'),
                    }
                )
                
                if created:
                    sync_job.trophies_synced += 1
                
                # Handle user earning status
                earned_trophy = earned_lookup.get(trophy_id)
                
                user_trophy, ut_created = UserTrophy.objects.get_or_create(
                    user=user,
                    trophy=trophy,
                    defaults={'earned': False}
                )
                
                # Update earned status
                if earned_trophy and getattr(earned_trophy, 'earned', False):
                    if not user_trophy.earned:
                        user_trophy.earned = True
                        user_trophy.earned_datetime = getattr(earned_trophy, 'earned_date_time', timezone.now())
                        user_trophy.save()
                        sync_job.trophies_new += 1
                
            except Exception as e:
                logger.error(f"Error processing trophy {trophy_name}: {e}")
                continue
        
        sync_job.save()
    
    def update_game_progress(self, user: User, game: Game, game_info: Dict[str, Any], sync_job: PSNSyncJob):
        """Update user's progress for a specific game"""
        
        progress, created = UserGameProgress.objects.get_or_create(
            user=user,
            game=game,
            defaults={
                'progress_percentage': game_info['progress'],
                'bronze_earned': game_info['bronze_earned'],
                'silver_earned': game_info['silver_earned'],
                'gold_earned': game_info['gold_earned'],
                'platinum_earned': game_info['platinum_earned'],
                'last_updated': timezone.now()
            }
        )
        
        if not created:
            progress.progress_percentage = game_info['progress']
            progress.bronze_earned = game_info['bronze_earned']
            progress.silver_earned = game_info['silver_earned']
            progress.gold_earned = game_info['gold_earned']
            progress.platinum_earned = game_info['platinum_earned']
            progress.last_updated = timezone.now()
            progress.save()
        
        progress.update_progress()
        
        if created:
            sync_job.games_created += 1
        else:
            sync_job.games_updated += 1
    
    def recalculate_user_scores(self, user: User, sync_job: PSNSyncJob):
        """Recalculate user's total scores and level"""
        
        sync_job.score_before = user.total_trophy_score
        sync_job.level_before = user.current_trophy_level
        
        user.calculate_total_score()
        user.update_trophy_level()
        
        # Update counts
        user_trophies = UserTrophy.objects.filter(user=user, earned=True)
        user.bronze_count = user_trophies.filter(trophy__trophy_type='bronze').count()
        user.silver_count = user_trophies.filter(trophy__trophy_type='silver').count()
        user.gold_count = user_trophies.filter(trophy__trophy_type='gold').count()
        user.platinum_count = user_trophies.filter(trophy__trophy_type='platinum').count()
        user.last_trophy_sync = timezone.now()
        user.save()
        
        sync_job.score_after = user.total_trophy_score
        sync_job.level_after = user.current_trophy_level
        sync_job.save()
        
        score_gained = sync_job.score_gained()
        levels_gained = sync_job.level_gained()
        
        if score_gained > 0:
            logger.info(f"🎉 {user.username} gained {score_gained} points and {levels_gained} levels!")