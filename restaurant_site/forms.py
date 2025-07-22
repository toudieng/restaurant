from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm
from .models import Utilisateur

class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Nom d'utilisateur")
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)

class RegisterForm(UserCreationForm):
    role = forms.ChoiceField(choices=Utilisateur.ROLE_CHOICES)

    class Meta(UserCreationForm):
        model = Utilisateur
        fields = UserCreationForm.Meta.fields + ('role',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['role'].initial = Utilisateur.CLIENT

class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))






