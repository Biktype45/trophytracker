from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
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
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'psn_id', 'profile_public', 'show_rare_trophies']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'psn_id': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_rare_trophies': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }