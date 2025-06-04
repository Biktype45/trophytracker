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
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
        
        # Update help texts
        self.fields['username'].help_text = ''
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''
    
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

# Alternative simple registration form without PSN requirement
class SimpleRegistrationForm(UserCreationForm):
    """Simple registration form without PSN requirement"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a unique username'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes and remove help texts
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
        
        # Clear help texts
        self.fields['username'].help_text = ''
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''
    
    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get('email')
        
        if email and User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists")
        
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
        return user