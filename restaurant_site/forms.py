from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm
from .models import Utilisateur
from .models import Categorie, Plat

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Nom d'utilisateur",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        label="Adresse email",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    role = forms.ChoiceField(
        choices=Utilisateur.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta(UserCreationForm.Meta):
        model = Utilisateur
        fields = UserCreationForm.Meta.fields + ('email', 'role')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].initial = Utilisateur.CLIENT
        self.fields['role'].disabled=True


class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

class AjoutPersonnelForm(UserCreationForm):
    class Meta:
        model = Utilisateur
        fields = ['username', 'role', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = [
            ('Serveur', 'Serveur'),
            ('Cuisinier', 'Cuisinier'),
            ('Caissier', 'Caissier')
        ]

class CategorieForm(forms.ModelForm):
    class Meta:
        model = Categorie
        fields = ['nom']

class PlatForm(forms.ModelForm):
    class Meta:
        model = Plat
        fields = ['nom', 'description', 'prix', 'image', 'allergenes', 'categorie', 'est_epuise', 'specialite_du_jour']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }