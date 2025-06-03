# =============================================================================
# File: psn_integration/tasks.py
# Trophy Synchronization Tasks - Phase 2
# =============================================================================

from django.utils import timezone
from django.db import transaction
from .models import PSNToken, PSNSyncLog
from .services import PSNAPIService, PSNAuthenticationService
from games.models import Game
from trophies.models import Trophy, UserTrophy, UserGameProgress
from users.models import User
from datetime import timedelta
import logging
from dateutil import parser

logger = logging.getLogger(__name__)

def sync_user_trophies_task(user_id, sync_log_id):
    """
    Sync user trophies from PlayStation Network
    This is the main trophy synchronization function
    """
    try:
        user = User.objects.get(id=user_id)
        sync_log = PSNSyncLog.objects.get(id=sync_log_id)
        psn_token = PSNToken.objects.get(user=user, is_active=True)
        
        logger.info(f"Starting trophy sync for user {user.username}")
        
        # Check if token needs refresh
        if psn_token.is_expired():
            logger.info(f"Token expired for user {user.username}, refreshing...")
            refresh_result = refresh_psn_token(psn_token)
            if not refresh_result:
                raise Exception("Failed to refresh expired token")
        
        # Initialize API service
        access_token = psn_token.get_access_token()
        api_service = PSNAPIService(access_token)
        
        games_processed = 0
        trophies_updated = 0
        new_trophies_earned = 0
        errors = []
        
        # Get user's trophy titles with pagination
        offset = 0
        limit = 50
        
        while True:
            try:
                logger.info(f"Fetching trophy titles (offset: {offset})")
                response = api_service.get_user_trophy_titles(limit=limit, offset=offset)
                trophy_titles = response.get('trophyTitles', [])
                
                if not trophy_titles:
                    logger.info("No more trophy titles found, sync complete")
                    break
                
                # Process each game
                for title_data in trophy_titles:
                    try:
                        result = process_single_game_trophies(user, api_service, title_data)
                        games_processed += 1
                        trophies_updated += result['trophies_updated']
                        new_trophies_earned += result['new_trophies']
                        
                        # Update sync log progress periodically
                        if games_processed % 10 == 0:
                            sync_log.games_processed = games_processed
                            sync_log.trophies_updated = trophies_updated
                            sync_log.new_trophies_earned = new_trophies_earned
                            sync_log.save()
                        
                        # Rate limiting
                        api_service.rate_limit_wait()
                        
                    except Exception as e:
                        error_msg = f"Error processing game {title_data.get('npCommunicationId', 'unknown')}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        
                        # Continue with other games even if one fails
                        continue
                
                offset += limit
                
                # Safety limit to prevent infinite loops
                if offset > 2000:  # Max 2000 games
                    logger.warning(f"Reached safety limit of 2000 games for user {user.username}")
                    break
                
            except Exception as e:
                error_msg = f"Error fetching trophy titles at offset {offset}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                break
        
        # Update user statistics
        logger.info(f"Updating user statistics for {user.username}")
        update_user_trophy_statistics(user)
        
        # Mark sync as completed
        status = 'success' if not errors else 'partial'
        sync_log.games_processed = games_processed
        sync_log.trophies_updated = trophies_updated
        sync_log.new_trophies_earned = new_trophies_earned
        sync_log.sync_data = {'errors': errors[:10]}  # Store first 10 errors
        sync_log.mark_completed(status)
        
        # Update PSN token sync info
        psn_token.last_sync = timezone.now()
        psn_token.sync_errors = len(errors)
        psn_token.save()
        
        logger.info(f"Trophy sync completed for {user.username}: {games_processed} games, {trophies_updated} trophies, {new_trophies_earned} new")
        
        return {
            'status': status,
            'games_processed': games_processed,
            'trophies_updated': trophies_updated,
            'new_trophies_earned': new_trophies_earned,
            'errors': errors,
        }
        
    except Exception as e:
        logger.error(f"Trophy sync task failed for user {user_id}: {e}")
        try:
            sync_log = PSNSyncLog.objects.get(id=sync_log_id)
            sync_log.status = 'failed'
            sync_log.error_message = str(e)
            sync_log.mark_completed('failed')
        except:
            pass
        raise

def process_single_game_trophies(user, api_service, title_data):
    """Process trophies for a single game"""
    np_communication_id = title_data['npCommunicationId']
    
    logger.info(f"Processing game: {title_data.get('trophyTitleName', 'Unknown')} ({np_communication_id})")
    
    # Get or create game with proper defaults
    game_defaults = {
        'title': title_data.get('trophyTitleName', 'Unknown Game'),
        'platform': title_data.get('trophyTitlePlatform', 'PS5'),
        'icon_url': title_data.get('trophyTitleIconUrl', ''),
        'has_trophy_groups': title_data.get('hasTrophyGroups', False),
        'trophy_set_version': title_data.get('trophySetVersion', '01.00'),
        'bronze_count': title_data.get('definedTrophies', {}).get('bronze', 0),
        'silver_count': title_data.get('definedTrophies', {}).get('silver', 0),
        'gold_count': title_data.get('definedTrophies', {}).get('gold', 0),
        'platinum_count': title_data.get('definedTrophies', {}).get('platinum', 0),
        'difficulty_multiplier': 3.0,  # Default AAA standard
    }
    
    game, created = Game.objects.get_or_create(
        np_communication_id=np_communication_id,
        defaults=game_defaults
    )
    
    if created:
        logger.info(f"Created new game: {game.title}")
    
    trophies_updated = 0
    new_trophies_earned = 0
    
    try:
        # Get trophies for this game
        trophies_response = api_service.get_game_trophies(np_communication_id)
        earned_response = api_service.get_user_earned_trophies(np_communication_id)
        
        # Create lookup dict for earned trophies
        earned_trophies = {t['trophyId']: t for t in earned_response.get('trophies', [])}
        game_trophies = trophies_response.get('trophies', [])
        
        logger.info(f"Processing {len(game_trophies)} trophies for {game.title}")
        
        # Process each trophy
        for trophy_data in game_trophies:
            trophy_id = trophy_data['trophyId']
            
            # Get or create trophy
            trophy_defaults = {
                'name': trophy_data.get('trophyName', 'Unknown Trophy'),
                'description': trophy_data.get('trophyDetail', ''),
                'trophy_type': trophy_data.get('trophyType', 'bronze'),
                'icon_url': trophy_data.get('trophyIconUrl', ''),
                'hidden': trophy_data.get('trophyHidden', False),
                'trophy_group_id': trophy_data.get('trophyGroupId', 'default'),
                'has_progress_target': 'trophyProgressTargetValue' in trophy_data,
                'progress_target_value': trophy_data.get('trophyProgressTargetValue'),
            }
            
            trophy, trophy_created = Trophy.objects.get_or_create(
                game=game,
                trophy_id=trophy_id,
                defaults=trophy_defaults
            )
            
            # Get or create user trophy record
            user_trophy, ut_created = UserTrophy.objects.get_or_create(
                user=user,
                trophy=trophy,
                defaults={'earned': False}
            )
            
            # Update earning status from API data
            earned_data = earned_trophies.get(trophy_id)
            if earned_data:
                old_earned = user_trophy.earned
                user_trophy.earned = earned_data.get('earned', False)
                
                # Parse earned datetime
                if user_trophy.earned and earned_data.get('earnedDateTime'):
                    try:
                        user_trophy.earned_datetime = parser.parse(earned_data['earnedDateTime'])
                    except Exception as e:
                        logger.warning(f"Failed to parse earned datetime: {e}")
                
                # Handle progress tracking (PS5 feature)
                if 'progress' in earned_data:
                    user_trophy.progress_value = earned_data.get('progress')
                    user_trophy.progress_rate = earned_data.get('progressRate')
                    
                    if earned_data.get('progressedDateTime'):
                        try:
                            user_trophy.progress_datetime = parser.parse(earned_data['progressedDateTime'])
                        except Exception as e:
                            logger.warning(f"Failed to parse progress datetime: {e}")
                
                user_trophy.save()
                trophies_updated += 1
                
                # Count new trophies
                if user_trophy.earned and not old_earned:
                    new_trophies_earned += 1
                    logger.info(f"New trophy earned: {trophy.name} ({trophy.trophy_type})")
        
        # Update user's game progress
        update_user_game_progress(user, game)
        
        logger.info(f"Completed processing {game.title}: {trophies_updated} trophies updated, {new_trophies_earned} new")
        
    except Exception as e:
        logger.error(f"Error processing trophies for game {np_communication_id}: {e}")
        raise
    
    return {
        'trophies_updated': trophies_updated,
        'new_trophies': new_trophies_earned,
    }

def update_user_game_progress(user, game):
    """Update or create user's progress for a specific game"""
    try:
        progress, created = UserGameProgress.objects.get_or_create(
            user=user,
            game=game
        )
        progress.update_progress()
        
        if created:
            logger.info(f"Created game progress record for {user.username} - {game.title}")
        
    except Exception as e:
        logger.error(f"Error updating game progress for {game.title}: {e}")

def update_user_trophy_statistics(user):
    """Update user's overall trophy statistics and level"""
    try:
        with transaction.atomic():
            # Count trophies by type
            user_trophies = UserTrophy.objects.filter(user=user, earned=True).select_related('trophy')
            
            bronze_count = user_trophies.filter(trophy__trophy_type='bronze').count()
            silver_count = user_trophies.filter(trophy__trophy_type='silver').count()
            gold_count = user_trophies.filter(trophy__trophy_type='gold').count()
            platinum_count = user_trophies.filter(trophy__trophy_type='platinum').count()
            
            # Update trophy counts
            user.bronze_count = bronze_count
            user.silver_count = silver_count
            user.gold_count = gold_count
            user.platinum_count = platinum_count
            
            # Calculate total score and update level
            user.calculate_total_score()
            user.update_trophy_level()
            
            logger.info(f"Updated statistics for {user.username}: {bronze_count}B/{silver_count}S/{gold_count}G/{platinum_count}P, Score: {user.total_trophy_score}, Level: {user.current_trophy_level}")
            
    except Exception as e:
        logger.error(f"Error updating user statistics for {user.username}: {e}")
        raise

def refresh_psn_token(psn_token):
    """Refresh an expired PSN token"""
    try:
        auth_service = PSNAuthenticationService()
        refresh_token = psn_token.get_refresh_token()
        
        logger.info(f"Refreshing PSN token for user {psn_token.user.username}")
        new_token_data = auth_service.refresh_access_token(refresh_token)
        
        # Update token
        expires_at = timezone.now() + timedelta(seconds=new_token_data['expires_in'])
        psn_token.set_access_token(new_token_data['access_token'])
        psn_token.set_refresh_token(new_token_data['refresh_token'])
        psn_token.expires_at = expires_at
        psn_token.save()
        
        logger.info(f"Successfully refreshed PSN token for user {psn_token.user.username}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to refresh PSN token for user {psn_token.user.username}: {e}")
        psn_token.is_active = False
        psn_token.save()
        return False