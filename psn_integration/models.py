# psn_integration/models.py - COMPLETE VERSION FOR PSNAWP
"""
Complete models for PSNAWP integration including all admin-referenced models
"""

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class PSNToken(models.Model):
    """Store NPSSO tokens for PSNAWP integration"""
    
    ACCOUNT_TYPES = [
        ('dedicated', 'Dedicated Service Account'),
        ('backup', 'Backup Service Account'),
    ]
    
    account_type = models.CharField(
        max_length=20, 
        choices=ACCOUNT_TYPES, 
        default='dedicated',
        help_text="Type of PSN account this token belongs to"
    )
    
    # NPSSO token (stored as access_token for compatibility)
    access_token = models.TextField(
        help_text="NPSSO token for PSNAWP authentication"
    )
    npsso_token = models.TextField(
        blank=True,
        help_text="Copy of NPSSO token for explicit reference"
    )
    
    # We don't need refresh tokens with PSNAWP/NPSSO
    refresh_token = models.TextField(
        blank=True, 
        null=True, 
        help_text="Not used with PSNAWP but kept for compatibility"
    )
    expires_at = models.DateTimeField(
        help_text="When this NPSSO token expires (usually ~60 days)"
    )
    
    # PSN Account metadata
    psn_account_id = models.CharField(
        max_length=100, 
        blank=True,
        help_text="PSN account ID associated with this token"
    )
    psn_username = models.CharField(
        max_length=50, 
        blank=True,
        help_text="PSN username for this account"
    )
    
    # Token status and tracking
    active = models.BooleanField(
        default=True,
        help_text="Whether this token is currently active"
    )
    last_used = models.DateTimeField(
        auto_now=True,
        help_text="Last time this token was used for API calls"
    )
    api_calls_count = models.IntegerField(
        default=0,
        help_text="Number of API calls made with this token"
    )
    
    # PSNAWP specific tracking
    psnawp_version = models.CharField(
        max_length=20,
        blank=True,
        help_text="Version of PSNAWP used with this token"
    )
    last_error = models.TextField(
        blank=True,
        help_text="Last error encountered with this token"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'psn_integration_token'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['account_type', 'active']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        status = "Active" if self.active and not self.is_expired() else "Inactive"
        return f"NPSSO Token ({self.account_type}) - {status} - Expires: {self.expires_at}"
    
    def is_expired(self):
        """Check if NPSSO token has expired"""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """Check if token is active and not expired"""
        return self.active and not self.is_expired()
    
    def increment_usage(self):
        """Increment API call counter"""
        self.api_calls_count += 1
        self.save(update_fields=['api_calls_count', 'last_used'])
    
    def save(self, *args, **kwargs):
        """Auto-populate npsso_token field"""
        if not self.npsso_token and self.access_token:
            self.npsso_token = self.access_token
        super().save(*args, **kwargs)


class PSNSyncJob(models.Model):
    """Track trophy synchronization jobs for users - PSNAWP compatible"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Job identification
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sync_jobs'
    )
    job_id = models.UUIDField(
        default=uuid.uuid4, 
        unique=True, 
        editable=False
    )
    
    # Job configuration
    sync_type = models.CharField(
        max_length=20,
        choices=[
            ('full', 'Full Sync'),
            ('incremental', 'Incremental Sync'),
            ('manual', 'Manual Sync'),
            ('scheduled', 'Scheduled Sync'),
        ],
        default='manual'
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal'
    )
    
    # Job status
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    progress_percentage = models.IntegerField(
        default=0, 
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    current_task = models.CharField(
        max_length=200, 
        blank=True,
        help_text="Current operation being performed"
    )
    
    # Sync results and statistics
    games_found = models.IntegerField(
        default=0,
        help_text="Number of games found in user's profile"
    )
    games_created = models.IntegerField(
        default=0,
        help_text="Number of new games added to database"
    )
    games_updated = models.IntegerField(
        default=0,
        help_text="Number of existing games that were updated"
    )
    trophies_synced = models.IntegerField(
        default=0,
        help_text="Total number of trophies processed"
    )
    trophies_new = models.IntegerField(
        default=0,
        help_text="Number of newly earned trophies found"
    )
    score_before = models.IntegerField(
        default=0,
        help_text="User's score before sync"
    )
    score_after = models.IntegerField(
        default=0,
        help_text="User's score after sync"
    )
    level_before = models.IntegerField(
        default=1,
        help_text="User's level before sync"
    )
    level_after = models.IntegerField(
        default=1,
        help_text="User's level after sync"
    )
    
    # Error tracking
    errors_count = models.IntegerField(
        default=0,
        help_text="Number of errors encountered during sync"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Details of any errors that occurred"
    )
    warnings = models.JSONField(
        default=list,
        blank=True,
        help_text="Non-fatal warnings during sync"
    )
    
    # PSNAWP specific tracking
    psnawp_calls_made = models.IntegerField(
        default=0,
        help_text="Number of PSNAWP API calls made during sync"
    )
    psnawp_errors = models.JSONField(
        default=list,
        blank=True,
        help_text="PSNAWP specific errors encountered"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'psn_integration_syncjob'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['job_id']),
        ]
    
    def __str__(self):
        return f"Sync Job {self.job_id} - {self.user.username} ({self.status})"
    
    def duration(self):
        """Calculate job duration"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        elif self.started_at:
            return timezone.now() - self.started_at
        return None
    
    def duration_seconds(self):
        """Get duration in seconds"""
        duration = self.duration()
        return duration.total_seconds() if duration else 0
    
    def score_gained(self):
        """Calculate score gained during sync"""
        return self.score_after - self.score_before
    
    def level_gained(self):
        """Calculate levels gained during sync"""
        return self.level_after - self.level_before
    
    def mark_started(self):
        """Mark job as started"""
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
    
    def mark_completed(self, success=True):
        """Mark job as completed"""
        self.status = 'completed' if success else 'failed'
        self.completed_at = timezone.now()
        self.progress_percentage = 100 if success else self.progress_percentage
        self.save(update_fields=['status', 'completed_at', 'progress_percentage'])
    
    def update_progress(self, percentage, task=None):
        """Update job progress"""
        self.progress_percentage = min(percentage, 100)
        if task:
            self.current_task = task
        self.save(update_fields=['progress_percentage', 'current_task'])


class PSNUserValidation(models.Model):
    """Track PSN ID validation results and cache them - PSNAWP compatible"""
    
    VALIDATION_STATUS = [
        ('valid', 'Valid and Public'),
        ('private', 'Valid but Private'),
        ('not_found', 'Not Found'),
        ('error', 'Validation Error'),
    ]
    
    # PSN identification
    psn_id = models.CharField(
        max_length=50, 
        unique=True,
        help_text="PlayStation Network ID"
    )
    
    # Validation results
    validation_status = models.CharField(
        max_length=20,
        choices=VALIDATION_STATUS,
        default='error'
    )
    is_valid = models.BooleanField(
        default=False,
        help_text="Whether PSN ID exists and is accessible"
    )
    is_public = models.BooleanField(
        default=False,
        help_text="Whether profile is set to public"
    )
    
    # PSN profile information
    psn_account_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Internal PSN account ID"
    )
    display_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Display name from PSN profile"
    )
    avatar_url = models.URLField(
        blank=True,
        help_text="URL to user's PSN avatar"
    )
    
    # Trophy information from validation
    trophy_level = models.IntegerField(
        null=True, 
        blank=True,
        help_text="User's current PSN trophy level"
    )
    total_trophies = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Trophy counts by type: {bronze: 0, silver: 0, gold: 0, platinum: 0}"
    )
    trophy_points = models.IntegerField(
        null=True,
        blank=True,
        help_text="Official PSN trophy points"
    )
    
    # Validation metadata
    last_checked = models.DateTimeField(auto_now=True)
    check_count = models.IntegerField(
        default=1,
        help_text="Number of times this PSN ID has been validated"
    )
    first_seen = models.DateTimeField(auto_now_add=True)
    
    # Error tracking
    last_error = models.TextField(
        blank=True,
        help_text="Last error message encountered during validation"
    )
    consecutive_errors = models.IntegerField(
        default=0,
        help_text="Number of consecutive validation errors"
    )
    
    # Performance tracking
    avg_response_time = models.FloatField(
        null=True,
        blank=True,
        help_text="Average API response time for this PSN ID"
    )
    
    class Meta:
        db_table = 'psn_integration_uservalidation'
        ordering = ['-last_checked']
        indexes = [
            models.Index(fields=['psn_id']),
            models.Index(fields=['validation_status']),
            models.Index(fields=['is_valid', 'is_public']),
            models.Index(fields=['last_checked']),
        ]
    
    def __str__(self):
        return f"PSN ID: {self.psn_id} ({self.get_validation_status_display()})"
    
    def needs_revalidation(self, hours=24):
        """Check if validation is stale and needs refresh"""
        if not self.last_checked:
            return True
        
        time_since_check = timezone.now() - self.last_checked
        return time_since_check.total_seconds() > (hours * 3600)
    
    def mark_validation_success(self, data):
        """Mark successful validation and update data"""
        self.validation_status = 'valid' if data.get('is_public', False) else 'private'
        self.is_valid = True
        self.is_public = data.get('is_public', False)
        self.psn_account_id = data.get('account_id')
        self.display_name = data.get('display_name', '')
        self.avatar_url = data.get('avatar_url', '')
        self.trophy_level = data.get('trophy_level')
        self.total_trophies = data.get('total_trophies', {})
        self.trophy_points = data.get('trophy_points')
        self.consecutive_errors = 0
        self.last_error = ''
        self.check_count += 1
        self.save()
    
    def mark_validation_error(self, error_message, status='error'):
        """Mark validation error"""
        self.validation_status = status
        self.is_valid = False
        self.is_public = False
        self.last_error = error_message
        self.consecutive_errors += 1
        self.check_count += 1
        self.save()


class PSNApiCall(models.Model):
    """Track PSN API calls for monitoring and rate limiting - PSNAWP compatible"""
    
    CALL_TYPES = [
        ('validate_user', 'User Validation'),
        ('trophy_summary', 'Trophy Summary'),
        ('game_list', 'Game List'),
        ('game_trophies', 'Game Trophies'),
        ('user_trophies', 'User Game Trophies'),
        ('trophy_groups', 'Trophy Groups'),
        ('psnawp_profile', 'PSNAWP Profile'),
        ('psnawp_titles', 'PSNAWP Trophy Titles'),
    ]
    
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('error', 'Error'),
        ('rate_limited', 'Rate Limited'),
        ('timeout', 'Timeout'),
    ]
    
    # Call identification
    call_type = models.CharField(max_length=20, choices=CALL_TYPES)
    endpoint = models.URLField(help_text="Full API endpoint called")
    
    # Request details
    psn_id = models.CharField(
        max_length=50, 
        blank=True,
        help_text="PSN ID being queried (if applicable)"
    )
    parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="API call parameters"
    )
    
    # Response details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    http_status_code = models.IntegerField(null=True, blank=True)
    response_time_ms = models.IntegerField(
        help_text="Response time in milliseconds"
    )
    response_size_bytes = models.IntegerField(
        null=True,
        blank=True,
        help_text="Size of response in bytes"
    )
    
    # Error details
    error_message = models.TextField(blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    
    # PSNAWP specific fields
    psnawp_method = models.CharField(
        max_length=100,
        blank=True,
        help_text="PSNAWP method called"
    )
    psnawp_version = models.CharField(
        max_length=20,
        blank=True,
        help_text="PSNAWP version used"
    )
    
    # Metadata
    user_agent = models.CharField(max_length=200, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Timestamps
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'psn_integration_apicall'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['call_type', 'timestamp']),
            models.Index(fields=['status', 'timestamp']),
            models.Index(fields=['psn_id', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.call_type} - {self.status} ({self.response_time_ms}ms)"
    
    @classmethod
    def log_call(cls, call_type, endpoint, status, response_time_ms, 
                 psn_id=None, parameters=None, http_status=None, 
                 error_message=None, response_size=None, psnawp_method=None):
        """Utility method to log an API call"""
        return cls.objects.create(
            call_type=call_type,
            endpoint=endpoint,
            psn_id=psn_id or '',
            parameters=parameters or {},
            status=status,
            http_status_code=http_status,
            response_time_ms=response_time_ms,
            response_size_bytes=response_size,
            error_message=error_message or '',
            psnawp_method=psnawp_method or ''
        )


class PSNRateLimit(models.Model):
    """Track rate limiting for PSN API - PSNAWP compatible"""
    
    # Rate limit tracking
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()
    calls_made = models.IntegerField(default=0)
    calls_limit = models.IntegerField(default=300)  # 300 calls per 15 minutes
    
    # Status
    limit_exceeded = models.BooleanField(default=False)
    reset_time = models.DateTimeField(null=True, blank=True)
    
    # PSNAWP specific tracking
    psnawp_calls = models.IntegerField(
        default=0,
        help_text="Number of PSNAWP calls in this window"
    )
    psnawp_errors = models.IntegerField(
        default=0,
        help_text="Number of PSNAWP errors in this window"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'psn_integration_ratelimit'
        ordering = ['-window_start']
    
    def __str__(self):
        return f"Rate Limit Window: {self.calls_made}/{self.calls_limit} calls"
    
    def can_make_call(self):
        """Check if we can make another API call"""
        if timezone.now() > self.window_end:
            return True  # Window expired, can make calls
        
        return self.calls_made < self.calls_limit
    
    def increment_calls(self, is_psnawp=True):
        """Increment call count"""
        self.calls_made += 1
        if is_psnawp:
            self.psnawp_calls += 1
        
        if self.calls_made >= self.calls_limit:
            self.limit_exceeded = True
        self.save()


class PSNGameDifficultyHint(models.Model):
    """Store difficulty hints for games discovered through PSN API - PSNAWP compatible"""
    
    # Game identification
    np_communication_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="PlayStation game identifier"
    )
    game_title = models.CharField(max_length=200)
    
    # Difficulty indicators from various sources
    completion_rate = models.FloatField(
        null=True,
        blank=True,
        help_text="Percentage of players who earned platinum"
    )
    average_completion_time = models.FloatField(
        null=True,
        blank=True,
        help_text="Average time to complete in hours"
    )
    trophy_rarity_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Average rarity of all trophies (0-100)"
    )
    
    # PSNAWP specific data
    psnawp_user_count = models.IntegerField(
        default=0,
        help_text="Number of users we've seen play this game via PSNAWP"
    )
    psnawp_completion_rate = models.FloatField(
        null=True,
        blank=True,
        help_text="Completion rate calculated from PSNAWP user data"
    )
    
    # Calculated difficulty
    suggested_multiplier = models.FloatField(
        default=3.0,
        help_text="AI/algorithm suggested difficulty multiplier"
    )
    confidence_score = models.FloatField(
        default=0.0,
        help_text="Confidence in suggested multiplier (0-1)"
    )
    
    # Data sources
    data_sources = models.JSONField(
        default=list,
        help_text="List of sources used for difficulty calculation"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'psn_integration_gamedhint'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['np_communication_id']),
            models.Index(fields=['suggested_multiplier']),
            models.Index(fields=['confidence_score']),
        ]
    
    def __str__(self):
        return f"{self.game_title} - Suggested: {self.suggested_multiplier}x"
    
    def update_from_psnawp_data(self, user_progress_data):
        """Update difficulty hint based on new PSNAWP user data"""
        self.psnawp_user_count += 1
        
        # Recalculate completion rate based on user data
        # This would involve more complex logic to track user progress
        
        # Update data sources
        if 'psnawp' not in self.data_sources:
            self.data_sources.append('psnawp')
        
        self.save()