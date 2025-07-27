from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group
from django.contrib import messages
from .forms import LoginForm, RegisterForm, CustomPasswordResetForm
from .models import Utilisateur
from django.core.mail import send_mail
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import login_required 
from .models import Plat, Reservation

def accueil_view(request): # Nouvelle vue pour l'accueil
    return render(request, 'authentification/accueil.html')

def auth_view(request):
    login_form = LoginForm()
    register_form = RegisterForm()

    if request.method == 'POST':
        # ------------- Connexion ----------------
        if 'login' in request.POST:
            login_form = LoginForm(request, data=request.POST)
            username = request.POST.get('username')
            password = request.POST.get('password')

            # Vérification manuelle de l'utilisateur
            try:
                user = Utilisateur.objects.get(username=username)
            except Utilisateur.DoesNotExist:
                messages.error(request, "Ce compte n'existe pas. Veuillez créer un compte d'abord.")
                return render(request, 'authentification/connexion.html', {
                    'login_form': login_form,
                    'register_form': register_form,
                })

            # Si l'utilisateur existe, valider le mot de passe
            if login_form.is_valid():
                user = login_form.get_user()
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
            else:
                messages.error(request, "Mot de passe incorrect.")

        # ------------- Inscription ----------------
        elif 'register' in request.POST:
            register_form = RegisterForm(request.POST)
            if register_form.is_valid():
                user = register_form.save()
                login(request, user)
                messages.success(request, "Inscription réussie. Vous êtes maintenant connecté.")

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
            else:
                messages.error(request, "Erreur lors de l'inscription. Veuillez corriger les erreurs.")

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

def client(request):
    return render(request, 'client/client.html')

def menu(request):
    plats = Plat.objects.all().order_by('nom')
    panier_count = sum(item['quantite'] for item in request.session.get('panier', {}).values())
    context = {
        'plats': plats,
        'panier_count': panier_count
    }
    return render(request, 'client/menu.html', context)

def ajouter_au_panier(request, plat_id):
    plat = get_object_or_404(Plat, id=plat_id)
    panier = request.session.get('panier', {})
    
    if str(plat.id) in panier:
        panier[str(plat.id)]['quantite'] += 1
    else:
        panier[str(plat.id)] = {
            'nom': plat.nom,
            'prix': str(plat.prix),
            'quantite': 1
        }
    
    request.session['panier'] = panier
    return redirect('menu') 

def voir_panier(request):
    panier = request.session.get('panier', {})
    total = sum(float(item['prix']) * item['quantite'] for item in panier.values())
    panier_count = sum(item['quantite'] for item in panier.values())

    reservations = None
    if request.user.is_authenticated:
        # On ne filtre plus par "est_confirmee" pour le moment
        reservations = Reservation.objects.filter(client=request.user)
    
    context = {
        'panier': panier,
        'total': total,
        'panier_count': panier_count,
        'reservations': reservations, 
    }
    return render(request, 'client/panier.html', context)

@login_required
def valider_commande(request):
    if request.method == 'POST':
        panier = request.session.get('panier', {})
        if not panier:
            return redirect('menu')

        mode_commande = request.POST.get('mode_commande')
        telephone = request.POST.get('telephone')
        methode_paiement = request.POST.get('methode_paiement')
        
        adresse_livraison = None
        reservation = None

        if mode_commande == 'livraison':
            adresse_option = request.POST.get('adresse_option')
            if adresse_option == 'saisie':
                adresse_livraison = request.POST.get('adresse_input')
            elif adresse_option == 'carte':
                # Logique pour les coordonnées de la carte
                adresse_livraison = request.POST.get('coordonnees_livraison')
        else: # Service en salle
            reservation_id = request.POST.get('reservation_id')
            try:
                reservation = Reservation.objects.get(id=reservation_id, client=request.user)
            except Reservation.DoesNotExist:
                # Gérer le cas où la réservation n'existe pas
                return redirect('voir_panier')

        total = sum(float(item['prix']) * item['quantite'] for item in panier.values())

        # Création de la commande
        try:
            with transaction.atomic():
                commande = Commande.objects.create(
                    client=request.user,
                    mode_commande=mode_commande,
                    reservation=reservation,
                    adresse_livraison=adresse_livraison,
                    total_paiement=total
                )
                
                for plat_id_str, item in panier.items():
                    plat = Plat.objects.get(id=int(plat_id_str))
                    LigneDeCommande.objects.create(
                        commande=commande,
                        plat=plat,
                        quantite=item['quantite'],
                        total_ligne=float(item['prix']) * item['quantite']
                    )

                # Logique de gestion du paiement
                if methode_paiement == 'especes':
                    # Si c'est en espèces, on met directement le statut à 'en_cours'
                    commande.statut = 'en_cours'
                    commande.save()
                    # Vider le panier
                    del request.session['panier']
                    return render(request, 'client/confirmation_commande.html', {'commande': commande})
                else:
                    # Logique pour les paiements en ligne (Wave, Orange Money, KPay, Carte Bancaire)
                    # Laissez cette partie vide pour l'instant
                    return HttpResponse("Paiement en ligne en cours de développement.")

        except Exception as e:
            # En cas d'erreur, on peut annuler la transaction et retourner une erreur
            return HttpResponse(f"Une erreur s'est produite : {e}", status=500)

    else:
        return redirect('voir_panier')

def supprimer_du_panier(request, plat_id):
    panier = request.session.get('panier', {})
    plat_id_str = str(plat_id)
    
    if plat_id_str in panier:
        del panier[plat_id_str]
        request.session['panier'] = panier
        
    return redirect('voir_panier')

def modifier_quantite(request, plat_id, action):
    panier = request.session.get('panier', {})
    plat_id_str = str(plat_id)
    
    if plat_id_str in panier:
        quantite_actuelle = panier[plat_id_str]['quantite']
        
        if action == 'augmenter':
            panier[plat_id_str]['quantite'] += 1
        elif action == 'diminuer':
            if quantite_actuelle > 1:
                panier[plat_id_str]['quantite'] -= 1
            else:
                del panier[plat_id_str] # Supprime l'article si la quantité atteint 0
                
        request.session['panier'] = panier
        
    return redirect('voir_panier')

@login_required
def faire_reservation(request):
    if request.method == 'POST':
        # Traiter les données du formulaire de réservation
        date_res = request.POST.get('date_reservation')
        heure_res = request.POST.get('heure_reservation')
        nb_personnes = request.POST.get('nombre_personnes')
        
        # Créer l'objet Reservation
        reservation = Reservation.objects.create(
            client=request.user,
            date_reservation=date_res,
            heure_reservation=heure_res,
            nombre_personnes=nb_personnes
        )
        
        # Rediriger vers la page de confirmation ou vers le menu
        return redirect('menu') 
    
    # Rendre le formulaire de réservation
    return render(request, 'client/reservation.html')

def admin_login_view(request):
    form = LoginForm(request, data=request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        if user.role != 'Administrateur':
            messages.error(request, "Accès refusé. Ce compte n'est pas un administrateur.")
        else:
            login(request, user)
            return redirect('admin_dashboard')

    return render(request, 'authentification/admin_login.html', {'form': form})


# Seul un utilisateur avec le bon rôle accède à sa vue. /  Exemple : le cuisinier ne peut pas voir la vue des serveurs.
def role_required(role):
    def decorator(view_func):
        return user_passes_test(lambda u: u.is_authenticated and u.role == role)(view_func)
    return decorator

# @role_required('Cuisinier')
# def vue_cuisinier(request):