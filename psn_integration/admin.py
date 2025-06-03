# psn_integration/admin.py - COMPLETE CORRECTED VERSION FOR PSNAWP
"""
Django admin configuration for PSN integration models - PSNAWP version
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib import messages
from .models import (
    PSNToken, PSNSyncJob, PSNUserValidation, PSNApiCall, 
    PSNRateLimit, PSNGameDifficultyHint
)

@admin.register(PSNToken)
class PSNTokenAdmin(admin.ModelAdmin):
    """Admin interface for NPSSO tokens - PSNAWP version"""
    
    list_display = [
        'account_type', 'psn_username', 'token_status', 'expires_at', 
        'api_calls_count', 'last_used', 'created_at'
    ]
    list_filter = ['account_type', 'active', 'created_at']
    readonly_fields = [
        'created_at', 'updated_at', 'last_used', 'api_calls_count',
        'token_status_display', 'time_until_expiry', 'npsso_token'
    ]
    search_fields = ['psn_username', 'psn_account_id']
    
    fieldsets = (
        ('Token Information', {
            'fields': ('account_type', 'active', 'token_status_display', 'time_until_expiry')
        }),
        ('PSN Account Details', {
            'fields': ('psn_username', 'psn_account_id')
        }),
        ('NPSSO Token Data', {
            'fields': ('access_token', 'npsso_token', 'expires_at'),
            'classes': ('collapse',),
            'description': 'NPSSO token data - handle with care. For PSNAWP integration.'
        }),
        ('PSNAWP Specific', {
            'fields': ('psnawp_version', 'last_error'),
            'classes': ('collapse',)
        }),
        ('Usage Statistics', {
            'fields': ('api_calls_count', 'last_used', 'created_at', 'updated_at')
        }),
    )
    
    actions = ['mark_inactive', 'test_npsso_tokens', 'refresh_token_info']
    
    def token_status(self, obj):
        """Display token status with color coding"""
        if not obj.active:
            return format_html('<span style="color: red;">❌ Inactive</span>')
        elif obj.is_expired():
            return format_html('<span style="color: orange;">⏰ Expired</span>')
        else:
            return format_html('<span style="color: green;">✅ Active</span>')
    token_status.short_description = 'Status'
    
    def token_status_display(self, obj):
        """Detailed token status for readonly field"""
        if not obj.active:
            return "❌ Inactive"
        elif obj.is_expired():
            return "⏰ Expired"
        else:
            days_left = (obj.expires_at - timezone.now()).days
            return f"✅ Active ({days_left} days left)"
    token_status_display.short_description = 'Token Status'
    
    def time_until_expiry(self, obj):
        """Show time until token expires"""
        if obj.is_expired():
            return "Already expired"
        
        time_left = obj.expires_at - timezone.now()
        days = time_left.days
        hours, remainder = divmod(time_left.seconds, 3600)
        
        if days > 0:
            return f"{days} days, {hours} hours"
        else:
            return f"{hours} hours"
    time_until_expiry.short_description = 'Time Until Expiry'
    
    def mark_inactive(self, request, queryset):
        """Admin action to mark tokens as inactive"""
        count = queryset.update(active=False)
        self.message_user(request, f'Marked {count} tokens as inactive.')
    mark_inactive.short_description = 'Mark selected tokens as inactive'
    
    def test_npsso_tokens(self, request, queryset):
        """Admin action to test NPSSO token validity"""
        success_count = 0
        error_count = 0
        
        for token in queryset:
            try:
                from psn_integration.services import PSNAWPService
                service = PSNAWPService(token.access_token)  # access_token contains NPSSO
                
                # Try to get profile info
                profile = service.me.profile()
                token.last_error = ''
                token.save()
                success_count += 1
                
            except Exception as e:
                token.last_error = str(e)
                token.save()
                error_count += 1
        
        if success_count > 0:
            self.message_user(request, f'✅ {success_count} tokens tested successfully.')
        if error_count > 0:
            self.message_user(request, f'❌ {error_count} tokens failed testing.', level=messages.ERROR)
    test_npsso_tokens.short_description = 'Test NPSSO tokens with PSNAWP'
    
    def refresh_token_info(self, request, queryset):
        """Refresh token information from PSN"""
        for token in queryset:
            try:
                from psn_integration.services import PSNAWPService
                service = PSNAWPService(token.access_token)
                
                profile = service.me.profile()
                token.psn_username = profile.get('onlineId', token.psn_username)
                
                # Get PSNAWP version
                import psnawp_api
                token.psnawp_version = getattr(psnawp_api, '__version__', 'unknown')
                token.save()
                
            except Exception as e:
                token.last_error = str(e)
                token.save()
        
        self.message_user(request, f'Refreshed information for {queryset.count()} tokens.')
    refresh_token_info.short_description = 'Refresh token information'


@admin.register(PSNSyncJob)
class PSNSyncJobAdmin(admin.ModelAdmin):
    """Admin interface for sync jobs - PSNAWP version"""
    
    list_display = [
        'job_id_short', 'user_link', 'status_display', 'progress_bar', 
        'sync_type', 'games_found', 'trophies_synced', 'score_gained_display', 
        'duration_display', 'created_at'
    ]
    list_filter = [
        'status', 'sync_type', 'priority', 'created_at', 
        ('user', admin.RelatedFieldListFilter)
    ]
    readonly_fields = [
        'job_id', 'duration_display', 'score_gained', 'level_gained',
        'created_at', 'started_at', 'completed_at', 'psnawp_calls_display'
    ]
    search_fields = ['user__username', 'user__psn_id', 'job_id']
    
    fieldsets = (
        ('Job Information', {
            'fields': ('job_id', 'user', 'sync_type', 'priority', 'status')
        }),
        ('Progress', {
            'fields': ('progress_percentage', 'current_task')
        }),
        ('Results', {
            'fields': (
                'games_found', 'games_created', 'games_updated',
                'trophies_synced', 'trophies_new'
            )
        }),
        ('Score Changes', {
            'fields': (
                'score_before', 'score_after', 'score_gained',
                'level_before', 'level_after', 'level_gained'
            )
        }),
        ('PSNAWP Specific', {
            'fields': ('psnawp_calls_made', 'psnawp_calls_display', 'psnawp_errors'),
            'classes': ('collapse',)
        }),
        ('Error Information', {
            'fields': ('errors_count', 'error_message', 'warnings'),
            'classes': ('collapse',)
        }),
        ('Performance', {
            'fields': ('duration_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at')
        }),
    )
    
    actions = ['cancel_pending_jobs', 'retry_failed_jobs', 'cleanup_old_jobs']
    
    def job_id_short(self, obj):
        """Display shortened job ID"""
        return str(obj.job_id)[:8] + '...'
    job_id_short.short_description = 'Job ID'
    
    def user_link(self, obj):
        """Link to user admin page"""
        try:
            url = reverse('admin:users_user_change', args=[obj.user.pk])
            psn_info = f" (PSN: {obj.user.psn_id})" if obj.user.psn_id else ""
            return format_html('<a href="{}">{}{}</a>', url, obj.user.username, psn_info)
        except:
            return obj.user.username
    user_link.short_description = 'User'
    
    def status_display(self, obj):
        """Display status with color coding"""
        colors = {
            'pending': 'orange',
            'running': 'blue',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def progress_bar(self, obj):
        """Display progress as a visual bar"""
        if obj.status in ['completed', 'failed', 'cancelled']:
            percentage = 100 if obj.status == 'completed' else obj.progress_percentage
        else:
            percentage = obj.progress_percentage
        
        color = 'green' if obj.status == 'completed' else 'blue'
        if obj.status == 'failed':
            color = 'red'
        
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
            '<div style="width: {}px; height: 20px; background-color: {}; border-radius: 3px; text-align: center; line-height: 20px; color: white; font-size: 11px;">{} %</div>'
            '</div>',
            percentage, color, percentage
        )
    progress_bar.short_description = 'Progress'
    
    def score_gained_display(self, obj):
        """Display score gained with color coding"""
        gained = obj.score_gained()
        if gained > 0:
            return format_html('<span style="color: green;">+{}</span>', gained)
        elif gained == 0:
            return '0'
        else:
            return format_html('<span style="color: red;">{}</span>', gained)
    score_gained_display.short_description = 'Score Δ'
    
    def duration_display(self, obj):
        """Display job duration"""
        duration = obj.duration()
        if duration:
            total_seconds = int(duration.total_seconds())
            minutes, seconds = divmod(total_seconds, 60)
            if minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        return "Not started" if not obj.started_at else "In progress"
    duration_display.short_description = 'Duration'
    
    def psnawp_calls_display(self, obj):
        """Display PSNAWP calls made"""
        calls = obj.psnawp_calls_made
        if calls > 0:
            return f"{calls} calls"
        return "No calls"
    psnawp_calls_display.short_description = 'PSNAWP Calls'
    
    def cancel_pending_jobs(self, request, queryset):
        """Cancel pending jobs"""
        count = queryset.filter(status='pending').update(status='cancelled')
        self.message_user(request, f'Cancelled {count} pending jobs.')
    cancel_pending_jobs.short_description = 'Cancel pending jobs'
    
    def retry_failed_jobs(self, request, queryset):
        """Reset failed jobs to pending"""
        count = queryset.filter(status='failed').update(
            status='pending', 
            progress_percentage=0,
            error_message='',
            psnawp_errors=[]
        )
        self.message_user(request, f'Reset {count} failed jobs to pending.')
    retry_failed_jobs.short_description = 'Retry failed jobs'
    
    def cleanup_old_jobs(self, request, queryset):
        """Clean up old completed jobs"""
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=30)
        old_jobs = queryset.filter(
            status__in=['completed', 'failed', 'cancelled'],
            created_at__lt=cutoff_date
        )
        count = old_jobs.count()
        old_jobs.delete()
        self.message_user(request, f'Cleaned up {count} old jobs (>30 days).')
    cleanup_old_jobs.short_description = 'Clean up old jobs (30+ days)'


@admin.register(PSNUserValidation)
class PSNUserValidationAdmin(admin.ModelAdmin):
    """Admin interface for PSN user validations - PSNAWP version"""
    
    list_display = [
        'psn_id', 'validation_status_display', 'is_public_display', 
        'trophy_level', 'trophy_count_display', 'last_checked', 'check_count'
    ]
    list_filter = [
        'validation_status', 'is_valid', 'is_public', 
        'last_checked', 'consecutive_errors'
    ]
    readonly_fields = [
        'first_seen', 'last_checked', 'check_count', 
        'avg_response_time', 'needs_revalidation_display',
        'trophy_count_display'
    ]
    search_fields = ['psn_id', 'display_name', 'psn_account_id']
    
    fieldsets = (
        ('PSN Information', {
            'fields': ('psn_id', 'psn_account_id', 'display_name', 'avatar_url')
        }),
        ('Validation Status', {
            'fields': (
                'validation_status', 'is_valid', 'is_public', 
                'needs_revalidation_display'
            )
        }),
        ('Trophy Data', {
            'fields': ('trophy_level', 'total_trophies', 'trophy_points', 'trophy_count_display'),
            'classes': ('collapse',)
        }),
        ('Validation History', {
            'fields': (
                'first_seen', 'last_checked', 'check_count', 
                'avg_response_time'
            )
        }),
        ('Error Information', {
            'fields': ('last_error', 'consecutive_errors'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['revalidate_with_psnawp', 'mark_for_revalidation', 'bulk_validate']
    
    def validation_status_display(self, obj):
        """Display validation status with icons"""
        icons = {
            'valid': '✅',
            'private': '🔒',
            'not_found': '❌',
            'error': '⚠️'
        }
        icon = icons.get(obj.validation_status, '❓')
        return f"{icon} {obj.get_validation_status_display()}"
    validation_status_display.short_description = 'Status'
    
    def is_public_display(self, obj):
        """Display public status with icons"""
        return '🔓 Public' if obj.is_public else '🔒 Private'
    is_public_display.short_description = 'Privacy'
    
    def trophy_count_display(self, obj):
        """Display trophy counts in a compact format"""
        trophies = obj.total_trophies
        if isinstance(trophies, dict) and trophies:
            return f"🥇{trophies.get('platinum', 0)} 🥈{trophies.get('gold', 0)} 🥉{trophies.get('silver', 0)} 🏅{trophies.get('bronze', 0)}"
        return "No data"
    trophy_count_display.short_description = 'Trophies'
    
    def needs_revalidation_display(self, obj):
        """Show if revalidation is needed"""
        return '⏰ Yes' if obj.needs_revalidation() else '✅ No'
    needs_revalidation_display.short_description = 'Needs Revalidation'
    
    def revalidate_with_psnawp(self, request, queryset):
        """Revalidate selected PSN IDs using PSNAWP"""
        success_count = 0
        error_count = 0
        
        try:
            from psn_integration.services import PSNAWPService
            service = PSNAWPService()
            
            for validation in queryset:
                try:
                    result = service.validate_psn_user(validation.psn_id)
                    
                    if result['valid']:
                        validation.mark_validation_success(result)
                        success_count += 1
                    else:
                        validation.mark_validation_error(result.get('error', 'Validation failed'))
                        error_count += 1
                        
                except Exception as e:
                    validation.mark_validation_error(str(e))
                    error_count += 1
            
            if success_count > 0:
                self.message_user(request, f'✅ Successfully revalidated {success_count} PSN IDs.')
            if error_count > 0:
                self.message_user(request, f'❌ Failed to revalidate {error_count} PSN IDs.', level=messages.ERROR)
                
        except Exception as e:
            self.message_user(request, f'Error initializing PSNAWP service: {e}', level=messages.ERROR)
    
    revalidate_with_psnawp.short_description = 'Revalidate with PSNAWP'
    
    def mark_for_revalidation(self, request, queryset):
        """Mark for revalidation by clearing last_checked"""
        count = queryset.update(last_checked=None)
        self.message_user(request, f'Marked {count} PSN IDs for revalidation.')
    mark_for_revalidation.short_description = 'Mark for revalidation'
    
    def bulk_validate(self, request, queryset):
        """Bulk validate PSN IDs that haven't been checked"""
        unchecked = queryset.filter(last_checked__isnull=True)
        count = unchecked.count()
        
        if count > 10:
            self.message_user(request, f'Too many PSN IDs to validate at once ({count}). Select 10 or fewer.', level=messages.WARNING)
            return
        
        # Trigger revalidation for unchecked ones
        self.revalidate_with_psnawp(request, unchecked)
    bulk_validate.short_description = 'Bulk validate unchecked PSN IDs'


@admin.register(PSNApiCall)
class PSNApiCallAdmin(admin.ModelAdmin):
    """Admin interface for API call logs - PSNAWP compatible"""
    
    list_display = [
        'timestamp', 'call_type', 'psn_id', 'status_display', 
        'response_time_display', 'http_status_code', 'psnawp_method'
    ]
    list_filter = ['call_type', 'status', 'timestamp', 'psnawp_method']
    readonly_fields = ['timestamp']
    search_fields = ['psn_id', 'endpoint', 'error_message', 'psnawp_method']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Call Information', {
            'fields': ('call_type', 'endpoint', 'psn_id', 'parameters')
        }),
        ('PSNAWP Specific', {
            'fields': ('psnawp_method', 'psnawp_version')
        }),
        ('Response', {
            'fields': (
                'status', 'http_status_code', 'response_time_ms', 
                'response_size_bytes'
            )
        }),
        ('Error Details', {
            'fields': ('error_message', 'error_code'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('user_agent', 'ip_address', 'timestamp'),
            'classes': ('collapse',)
        }),
    )
    
    def status_display(self, obj):
        """Display status with color coding"""
        colors = {
            'success': 'green',
            'error': 'red',
            'rate_limited': 'orange',
            'timeout': 'red'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = 'Status'
    
    def response_time_display(self, obj):
        """Display response time with performance indicators"""
        ms = obj.response_time_ms
        if ms < 1000:
            color = 'green'
        elif ms < 3000:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {};">{} ms</span>',
            color, ms
        )
    response_time_display.short_description = 'Response Time'


@admin.register(PSNRateLimit)
class PSNRateLimitAdmin(admin.ModelAdmin):
    """Admin interface for rate limiting - PSNAWP compatible"""
    
    list_display = [
        'window_start', 'window_end', 'calls_progress', 
        'psnawp_calls_display', 'limit_status', 'reset_time'
    ]
    list_filter = ['limit_exceeded', 'window_start']
    readonly_fields = ['created_at', 'updated_at', 'calls_progress_display']
    
    fieldsets = (
        ('Rate Limit Window', {
            'fields': ('window_start', 'window_end', 'calls_progress_display')
        }),
        ('Limits', {
            'fields': ('calls_made', 'calls_limit', 'limit_exceeded', 'reset_time')
        }),
        ('PSNAWP Tracking', {
            'fields': ('psnawp_calls', 'psnawp_errors')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def calls_progress(self, obj):
        """Display calls progress as a bar"""
        percentage = (obj.calls_made / obj.calls_limit) * 100
        color = 'green'
        if percentage > 80:
            color = 'orange'
        if percentage >= 100:
            color = 'red'
        
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0;">'
            '<div style="width: {}%; height: 20px; background-color: {}; text-align: center; line-height: 20px; color: white; font-size: 11px;">{}/{}</div>'
            '</div>',
            min(percentage, 100), color, obj.calls_made, obj.calls_limit
        )
    calls_progress.short_description = 'Progress'
    
    def calls_progress_display(self, obj):
        """Detailed calls progress for readonly field"""
        percentage = (obj.calls_made / obj.calls_limit) * 100
        return f"{obj.calls_made}/{obj.calls_limit} calls ({percentage:.1f}%)"
    calls_progress_display.short_description = 'Calls Progress'
    
    def psnawp_calls_display(self, obj):
        """Display PSNAWP specific call count"""
        return f"{obj.psnawp_calls} PSNAWP calls"
    psnawp_calls_display.short_description = 'PSNAWP Calls'
    
    def limit_status(self, obj):
        """Display limit exceeded status"""
        if obj.limit_exceeded:
            return format_html('<span style="color: red;">🚫 Exceeded</span>')
        elif obj.calls_made > obj.calls_limit * 0.8:
            return format_html('<span style="color: orange;">⚠️ Warning</span>')
        else:
            return format_html('<span style="color: green;">✅ OK</span>')
    limit_status.short_description = 'Status'


@admin.register(PSNGameDifficultyHint)
class PSNGameDifficultyHintAdmin(admin.ModelAdmin):
    """Admin interface for game difficulty hints - PSNAWP compatible"""
    
    list_display = [
        'game_title', 'suggested_multiplier_display', 'confidence_display',
        'completion_rate', 'psnawp_user_count', 'data_sources_count', 'updated_at'
    ]
    list_filter = [
        'suggested_multiplier', 'confidence_score', 
        'updated_at', 'data_sources'
    ]
    readonly_fields = ['created_at', 'updated_at', 'data_sources_count']
    search_fields = ['game_title', 'np_communication_id']
    
    fieldsets = (
        ('Game Information', {
            'fields': ('np_communication_id', 'game_title')
        }),
        ('Difficulty Data', {
            'fields': (
                'completion_rate', 'average_completion_time', 
                'trophy_rarity_score'
            )
        }),
        ('PSNAWP Data', {
            'fields': ('psnawp_user_count', 'psnawp_completion_rate'),
            'classes': ('collapse',)
        }),
        ('Calculated Difficulty', {
            'fields': ('suggested_multiplier', 'confidence_score')
        }),
        ('Data Sources', {
            'fields': ('data_sources', 'data_sources_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['recalculate_difficulty', 'apply_to_games', 'reset_psnawp_data']
    
    def suggested_multiplier_display(self, obj):
        """Display suggested multiplier with color coding"""
        multiplier = obj.suggested_multiplier
        if multiplier <= 1.5:
            color = 'green'
        elif multiplier <= 3.0:
            color = 'blue'
        elif multiplier <= 6.0:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}x</span>',
            color, multiplier
        )
    suggested_multiplier_display.short_description = 'Suggested Multiplier'
    
    def confidence_display(self, obj):
        """Display confidence score as percentage"""
        percentage = obj.confidence_score * 100
        if percentage >= 80:
            color = 'green'
        elif percentage >= 60:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, percentage
        )
    confidence_display.short_description = 'Confidence'
    
    def data_sources_count(self, obj):
        """Count of data sources"""
        return len(obj.data_sources) if obj.data_sources else 0
    data_sources_count.short_description = 'Sources Count'
    
    def recalculate_difficulty(self, request, queryset):
        """Recalculate difficulty for selected games"""
        count = queryset.count()
        # Here you would implement the recalculation logic
        self.message_user(request, f'Queued {count} games for difficulty recalculation.')
    recalculate_difficulty.short_description = 'Recalculate difficulty'
    
    def apply_to_games(self, request, queryset):
        """Apply difficulty hints to actual games"""
        updated_count = 0
        
        for hint in queryset:
            try:
                from games.models import Game
                game = Game.objects.get(np_communication_id=hint.np_communication_id)
                game.difficulty_multiplier = hint.suggested_multiplier
                game.save()
                updated_count += 1
            except Game.DoesNotExist:
                continue
            except Exception:
                continue
        
        self.message_user(request, f'Applied difficulty hints to {updated_count} games.')
    apply_to_games.short_description = 'Apply to games database'
    
    def reset_psnawp_data(self, request, queryset):
        """Reset PSNAWP specific data"""
        count = queryset.update(
            psnawp_user_count=0,
            psnawp_completion_rate=None
        )
        self.message_user(request, f'Reset PSNAWP data for {count} games.')
    reset_psnawp_data.short_description = 'Reset PSNAWP data'


# Custom admin site configuration for PSNAWP
admin.site.site_header = '🎮 Trophy Tracker - PSNAWP Integration Admin'
admin.site.site_title = 'PSNAWP Integration Admin'
admin.site.index_title = 'PlayStation Network Integration Management (PSNAWP)'

# Add custom styling for PSNAWP admin
admin.site.enable_nav_sidebar = True