from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group
from django.contrib import messages
from .forms import LoginForm, RegisterForm, CustomPasswordResetForm
from .models import Utilisateur
from django.core.mail import send_mail

def accueil_view(request): # Nouvelle vue pour l'accueil
    return render(request, 'authentification/accueil.html')

def auth_view(request):
    login_form = LoginForm()
    register_form = RegisterForm()

    if request.method == 'POST':
        # Connexion
        if 'login' in request.POST:
            login_form = LoginForm(request, data=request.POST)
            if login_form.is_valid():
                user = login_form.get_user()
                login(request, user)

                # Redirection selon le rôle
                role = user.role
                if role == 'Administrateur':
                    return redirect('admin_dashboard')
                elif role == 'Client':
                    return redirect('client_dashboard')
                elif role == 'Serveur':
                    return redirect('serveur_dashboard')
                elif role == 'Cuisinier':
                    return redirect('cuisinier_dashboard')
                elif role == 'Caissier':
                    return redirect('caissier_dashboard')
                else:
                    return redirect('accueil')  # Par défaut

        # Inscription
        elif 'register' in request.POST:
            register_form = RegisterForm(request.POST)
            if register_form.is_valid():
                user = register_form.save()
                login(request, user)

                role = user.role
                if role == 'Administrateur':
                    return redirect('admin_dashboard')
                elif role == 'Client':
                    return redirect('client_dashboard')
                elif role == 'Serveur':
                    return redirect('serveur_dashboard')
                elif role == 'Cuisinier':
                    return redirect('cuisinier_dashboard')
                elif role == 'Caissier':
                    return redirect('caissier_dashboard')
                else:
                    return redirect('accueil')

    return render(request, 'authentification/connexion.html', {
        'login_form': login_form,
        'register_form': register_form,
    })


def register_view(request):
    login_form = LoginForm()  # Toujours défini

    if request.method == 'POST':
        if 'register' in request.POST:
            register_form = RegisterForm(request.POST)
            if register_form.is_valid():
                user = register_form.save()
                login(request, user)
                messages.success(request, 'Inscription réussie ! Vous êtes maintenant connecté.')
                return redirect('accueil')
            else:
                messages.error(request, 'Erreur lors de l\'inscription. Veuillez corriger les erreurs.')
        else:
            login_form = LoginForm(request, data=request.POST)
            register_form = RegisterForm()  # Pour éviter une variable non définie
            if login_form.is_valid():
                username = login_form.cleaned_data.get('username')
                password = login_form.cleaned_data.get('password')
                user = authenticate(username=username, password=password)
                if user is not None:
                    login(request, user)
                    messages.success(request, 'Connexion réussie !')
                    return redirect('accueil')
                else:
                    messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')
            else:
                messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect. Veuillez vérifier vos informations.')
    else:
        register_form = RegisterForm()
        login_form = LoginForm()

    return render(request, 'authentification/connexion.html', {
        'register_form': register_form,
        'login_form': login_form
    })


def logout(request):
    logout(request)
    messages.info(request, 'Vous avez été déconnecté.')
    return redirect('accueil')


def test_email(request):
    try:
        send_mail(
            subject='Test Email depuis Django',
            message='Ceci est un message de test envoyé depuis Django via Gmail.',
            from_email='tonemail@gmail.com',  # remplace par ton email
            recipient_list=['destinataire@example.com'],  # remplace par un email réel
            fail_silently=False,
        )
        message = "✅ Email envoyé avec succès."
        status = "success"
    except Exception as e:
        message = f"Erreur lors de l'envoi de l'email : {e}"
        status = "error"

    return render(request, 'renitialisation_password_terminer.html', {'message': message, 'status': status})