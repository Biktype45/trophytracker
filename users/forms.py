from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import User

class PSNRegistrationForm(UserCreationForm):
    """Registration form with required PSN ID for simplified flow"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    psn_id = forms.CharField(
        max_length=50, 
        required=True,
        help_text="Your PlayStation Network ID (must be public)",
        widget=forms.TextInput(attrs={
            'class': 'form-control psn-id-input',
            'placeholder': 'Enter your PSN ID'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'psn_id', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a unique username'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        # Add Bootstrap classes to password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    
    def clean_psn_id(self):
        """Validate PSN ID format and uniqueness"""
        psn_id = self.cleaned_data.get('psn_id')
        
        if psn_id:
            # Basic format validation
            if len(psn_id) < 3 or len(psn_id) > 16:
                raise ValidationError("PSN ID must be between 3 and 16 characters")
            
            # Check for invalid characters (basic check)
            if not psn_id.replace('_', '').replace('-', '').isalnum():
                raise ValidationError("PSN ID can only contain letters, numbers, hyphens, and underscores")
            
            # Check uniqueness
            if User.objects.filter(psn_id=psn_id).exists():
                raise ValidationError("This PSN ID is already connected to another account")
        
        return psn_id
    
    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get('email')
        
        if email and User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists")
        
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.psn_id = self.cleaned_data['psn_id']
        user.profile_public = True  # Set to public by default for PSN sync
        user.allow_trophy_sync = True  # Enable trophy sync by default
        
        if commit:
            user.save()
        return user

class CustomUserCreationForm(UserCreationForm):
    """Legacy form with optional PSN ID"""
    email = forms.EmailField(required=True)
    psn_id = forms.CharField(
        max_length=50, 
        required=False,
        help_text="Your PlayStation Network ID (can be added later)"
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'psn_id', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if self.cleaned_data['psn_id']:
            user.psn_id = self.cleaned_data['psn_id']
        if commit:
            user.save()
        return user

class UserProfileForm(forms.ModelForm):
    """Form for editing user profile information"""
    class Meta:
        model = User
        fields = [
            'first_name', 
            'last_name', 
            'email', 
            'psn_id', 
            'profile_public', 
            'show_rare_trophies',
            'allow_trophy_sync'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email address'
            }),
            'psn_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'PlayStation Network ID'
            }),
            'profile_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'show_rare_trophies': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'allow_trophy_sync': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        help_texts = {
            'psn_id': 'Your PlayStation Network username',
            'profile_public': 'Allow other users to view your trophy profile',
            'show_rare_trophies': 'Display rare and ultra-rare trophies prominently',
            'allow_trophy_sync': 'Enable automatic trophy synchronization'
        }
    
    def clean_psn_id(self):
        """Validate PSN ID if provided"""
        psn_id = self.cleaned_data.get('psn_id')
        
        if psn_id:
            # Basic format validation
            if len(psn_id) < 3 or len(psn_id) > 16:
                raise ValidationError("PSN ID must be between 3 and 16 characters")
            
            # Check uniqueness (exclude current user)
            if User.objects.filter(psn_id=psn_id).exclude(pk=self.instance.pk).exists():
                raise ValidationError("This PSN ID is already connected to another account")
        
        return psn_id

class PSNSettingsForm(forms.Form):
    """Form for PSN-specific settings"""
    psn_id = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'PlayStation Network ID'
        }),
        help_text="Your PlayStation Network username"
    )
    
    auto_sync = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text="Automatically sync trophies when visiting your profile"
    )
    
    sync_notifications = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text="Show notifications when new trophies are found"
    )
    
    include_hidden = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text="Sync and display hidden/secret trophies"
    )
    
    public_profile = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text="Make your trophy profile visible to other users"
    )
    
    def clean_psn_id(self):
        """Validate PSN ID format"""
        psn_id = self.cleaned_data.get('psn_id')
        
        if psn_id:
            if len(psn_id) < 3 or len(psn_id) > 16:
                raise ValidationError("PSN ID must be between 3 and 16 characters")
            
            if not psn_id.replace('_', '').replace('-', '').isalnum():
                raise ValidationError("PSN ID can only contain letters, numbers, hyphens, and underscores")
        
        return psn_id

class PSNValidationForm(forms.Form):
    """Form for validating PSN ID via AJAX"""
    psn_id = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter PSN ID to validate'
        })
    )
    
    def clean_psn_id(self):
        """Validate PSN ID format"""
        psn_id = self.cleaned_data.get('psn_id')
        
        if len(psn_id) < 3 or len(psn_id) > 16:
            raise ValidationError("PSN ID must be between 3 and 16 characters")
        
        if not psn_id.replace('_', '').replace('-', '').isalnum():
            raise ValidationError("PSN ID can only contain letters, numbers, hyphens, and underscores")
        
        return psn_id