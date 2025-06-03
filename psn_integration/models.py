# =============================================================================
# File: psn_integration/models.py
# PSN Integration Models for Secure Token Storage
# =============================================================================

from django.db import models
from django.conf import settings
from django.utils import timezone
from cryptography.fernet import Fernet
import base64
import json

class PSNToken(models.Model):
    """Secure storage for PSN authentication tokens"""
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='psn_token'
    )
    
    # Encrypted token storage
    encrypted_access_token = models.TextField()
    encrypted_refresh_token = models.TextField()
    
    # Token metadata
    token_type = models.CharField(max_length=20, default='Bearer')
    expires_at = models.DateTimeField()
    scope = models.TextField()
    
    # PSN user information
    psn_account_id = models.CharField(max_length=100, unique=True)
    psn_online_id = models.CharField(max_length=50)
    psn_avatar_url = models.URLField(blank=True, null=True)
    
    # Status tracking
    is_active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    sync_errors = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def _get_cipher(self):
        """Get encryption cipher"""
        key = settings.PSN_TOKEN_ENCRYPTION_KEY
        if isinstance(key, str):
            key = key.encode()
        # Ensure key is properly formatted for Fernet
        if len(key) != 44:  # Base64 encoded 32-byte key should be 44 chars
            # For development, create a proper key from the provided string
            key = base64.urlsafe_b64encode(key[:32].ljust(32, b'0'))
        return Fernet(key)
    
    def set_access_token(self, token):
        """Encrypt and store access token"""
        cipher = self._get_cipher()
        self.encrypted_access_token = cipher.encrypt(token.encode()).decode()
    
    def get_access_token(self):
        """Decrypt and return access token"""
        cipher = self._get_cipher()
        return cipher.decrypt(self.encrypted_access_token.encode()).decode()
    
    def set_refresh_token(self, token):
        """Encrypt and store refresh token"""
        cipher = self._get_cipher()
        self.encrypted_refresh_token = cipher.encrypt(token.encode()).decode()
    
    def get_refresh_token(self):
        """Decrypt and return refresh token"""
        cipher = self._get_cipher()
        return cipher.decrypt(self.encrypted_refresh_token.encode()).decode()
    
    def is_expired(self):
        """Check if token is expired"""
        return timezone.now() >= self.expires_at
    
    def __str__(self):
        return f"{self.user.username} - {self.psn_online_id}"
    
    class Meta:
        db_table = 'psn_integration_psntoken'
        verbose_name = 'PSN Token'
        verbose_name_plural = 'PSN Tokens'

class PSNSyncLog(models.Model):
    """Track PSN synchronization attempts and results"""
    
    SYNC_TYPES = [
        ('full', 'Full Trophy Sync'),
        ('incremental', 'Incremental Update'),
        ('profile', 'Profile Update'),
        ('manual', 'Manual Sync'),
    ]
    
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('success', 'Success'),
        ('partial', 'Partial Success'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='sync_logs'
    )
    
    sync_type = models.CharField(max_length=20, choices=SYNC_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='started')
    
    # Sync statistics
    games_processed = models.IntegerField(default=0)
    trophies_updated = models.IntegerField(default=0)
    new_trophies_earned = models.IntegerField(default=0)
    
    # Results and errors
    error_message = models.TextField(blank=True)
    sync_data = models.JSONField(default=dict)  # Store detailed sync info
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    
    def mark_completed(self, status='success'):
        """Mark sync as completed"""
        self.completed_at = timezone.now()
        self.status = status
        if self.started_at:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
        self.save()
    
    def get_duration_display(self):
        """Return human-readable duration"""
        if self.duration_seconds is None:
            return "In progress..."
        
        minutes = self.duration_seconds // 60
        seconds = self.duration_seconds % 60
        
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"
    
    def __str__(self):
        return f"{self.user.username} - {self.sync_type} - {self.status}"
    
    class Meta:
        db_table = 'psn_integration_psnsynclog'
        verbose_name = 'PSN Sync Log'
        verbose_name_plural = 'PSN Sync Logs'
        ordering = ['-started_at']