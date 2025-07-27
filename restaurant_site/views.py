from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib import messages
from django.urls import reverse
from django.db import transaction

from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Plat, Reservation, LigneDeCommande, Commande, Utilisateur
from .forms import LoginForm, RegisterForm, AjoutPersonnelForm


def role_required(role):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and request.user.role == role:
                return view_func(request, *args, **kwargs)
            return redirect('connexion')
        return _wrapped_view
    return decorator
    
# =============================================================
# VUES D'AUTHENTIFICATION ET DE BASE
# =============================================================

def accueil_view(request):
    return render(request, 'authentification/accueil.html')

@role_required('Client')
def client(request):
    return render(request, 'client/client.html')

def auth_view(request):
    login_form = LoginForm()
    register_form = RegisterForm()

    if request.method == 'POST':
        if 'login' in request.POST:
            login_form = LoginForm(request, data=request.POST)
            username = request.POST.get('username')
            password = request.POST.get('password')

            try:
                Utilisateur.objects.get(username=username)
            except Utilisateur.DoesNotExist:
                messages.error(request, "Ce compte n'existe pas. Veuillez créer un compte d'abord.")
                return render(request, 'authentification/connexion.html', {
                    'login_form': login_form,
                    'register_form': register_form,
                })

            if login_form.is_valid():
                user = login_form.get_user()
                login(request, user)

                role = user.role
                if role == 'Administrateur':
                    return redirect('/admin/')
                elif role == 'Client':
                    return redirect('client')
                elif role == 'Serveur':
                    return redirect('serveur')
                elif role == 'Cuisinier':
                    return redirect('cuisinier')
                elif role == 'Caissier':
                    return redirect('caissier')
                else:
                    return redirect('accueil')
            else:
                messages.error(request, "Mot de passe incorrect.")

        elif 'register' in request.POST:
            register_form = RegisterForm(request.POST)
            if register_form.is_valid():
                user = register_form.save()
                login(request, user)
                messages.success(request, "Inscription réussie. Vous êtes maintenant connecté.")

                role = user.role
                if role == 'Administrateur':
                    return redirect('/admin/')
                elif role == 'Client':
                    return redirect('client')
                elif role == 'Serveur':
                    return redirect('serveur')
                elif role == 'Cuisinier':
                    return redirect('cuisinier')
                elif role == 'Caissier':
                    return redirect('caissier')
                else:
                    return redirect('accueil')
            else:
                messages.error(request, "Erreur lors de l'inscription. Veuillez corriger les erreurs.")

    return render(request, 'authentification/connexion.html', {
        'login_form': login_form,
        'register_form': register_form,
    })

def logout_view(request):
    auth_logout(request)
    messages.success(request, "Déconnexion réussie.")
    return redirect('connexion')


# =============================================================
# VUES DU CLIENT
# =============================================================

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
    
    for plat_id, item in panier.items():
        item['total'] = float(item['prix']) * item['quantite']
    
    total_panier = sum(item['total'] for item in panier.values())
    
    context = {
        'panier': panier,
        'total_panier': total_panier,
    }
    return render(request, 'client/panier.html', context)

def modifier_quantite(request, plat_id):
    if request.method == 'POST':
        panier = request.session.get('panier', {})
        plat_id_str = str(plat_id)
        
        try:
            quantite = int(request.POST.get('quantite', 0))
            if quantite > 0:
                panier[plat_id_str]['quantite'] = quantite
                prix_unitaire = float(panier[plat_id_str]['prix'])
                panier[plat_id_str]['total'] = prix_unitaire * quantite
            else:
                del panier[plat_id_str]
            
            request.session['panier'] = panier
        except (ValueError, KeyError):
            pass 
    return redirect('voir_panier')

def supprimer_du_panier(request, plat_id):
    panier = request.session.get('panier', {})
    plat_id_str = str(plat_id)
    
    if plat_id_str in panier:
        del panier[plat_id_str]
    
    request.session['panier'] = panier
    return redirect('voir_panier')

@login_required
def faire_reservation(request):
    if request.method == 'POST':
        date_res = request.POST.get('date_reservation')
        heure_res = request.POST.get('heure_reservation')
        nb_personnes = request.POST.get('nombre_personnes')
        
        reservation = Reservation.objects.create(
            client=request.user,
            date_reservation=date_res,
            heure_reservation=heure_res,
            nombre_personnes=nb_personnes
        )
        
        messages.success(request, "Votre réservation a été enregistrée. En attente de confirmation.")
        return redirect('menu') 
    
    return render(request, 'client/reservation.html')


# =============================================================
# VUES DE COMMANDE ET DE PAIEMENT
# =============================================================

MODE_TEST_PAIEMENT = True

def handle_mock_payment(request, commande):
    print(f"Mode de test activé : Paiement simulé pour la commande #{commande.id}.")
    commande.statut = 'en_cours'
    commande.save()
    
    if 'panier' in request.session:
        del request.session['panier']
    
    return render(request, 'client/confirmation_commande.html', {'commande': commande})


@login_required
def validation_commande(request):
    panier = request.session.get('panier', {})
    if not panier:
        return redirect('menu')

    total = sum(float(item['prix']) * item['quantite'] for item in panier.values())
    reservations = Reservation.objects.filter(client=request.user, est_confirmee=True)

    context = {
        'panier': panier,
        'total': total,
        'reservations': reservations
    }
    return render(request, 'client/validation_commande.html', context)


@login_required
def traitement_commande(request):
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
                adresse_livraison = request.POST.get('coordonnees_livraison')
        elif mode_commande == 'salle':
            reservation_id = request.POST.get('reservation_id')
            if reservation_id and reservation_id != 'none':
                try:
                    reservation = Reservation.objects.get(id=reservation_id, client=request.user)
                except Reservation.DoesNotExist:
                    messages.error(request, "Réservation invalide.")
                    return redirect('voir_panier')

        total = sum(float(item['prix']) * item['quantite'] for item in panier.values())

        try:
            with transaction.atomic():
                commande = Commande.objects.create(
                    client=request.user,
                    mode_commande=mode_commande,
                    reservation=reservation,
                    adresse_livraison=adresse_livraison,
                    total_paiement=total,
                    statut='en_attente'
                )
                
                for plat_id_str, item in panier.items():
                    plat = Plat.objects.get(id=int(plat_id_str))
                    LigneDeCommande.objects.create(
                        commande=commande,
                        plat=plat,
                        quantite=item['quantite'],
                        prix_unitaire=plat.prix,
                        total_ligne=float(item['prix']) * item['quantite']
                    )

                if methode_paiement == 'especes':
                    commande.statut = 'en_cours'
                    commande.save()
                    if 'panier' in request.session:
                        del request.session['panier']
                    return render(request, 'client/confirmation_commande.html', {'commande': commande})
                
                elif methode_paiement in ['wave', 'orange_money', 'kpay', 'carte_bancaire']:
                    if MODE_TEST_PAIEMENT:
                        return handle_mock_payment(request, commande)
                    else:
                        return HttpResponse(f"Paiement {methode_paiement} en cours d'intégration...")
                
                else:
                    return HttpResponse("Méthode de paiement non valide.", status=400)

        except Plat.DoesNotExist:
            return HttpResponse("Erreur : Un des plats n'existe pas.", status=400)
        except Exception as e:
            return HttpResponse(f"Une erreur s'est produite : {e}", status=500)

    return redirect('voir_panier')

# =============================================================
# VUES D'ADMINISTRATION
# =============================================================


def client(request):
    return render(request, )

@role_required('Serveur')
def serveur_dashboard(request):
    return render(request, 'serveur.html')

@role_required('Cuisinier')
def cuisinier_dashboard(request):
    return render(request, 'cuisinier/cuisinier.html')

@role_required('Caissier')
def caissier_dashboard(request):
    return render(request, 'caissier.html')

<<<<<<< Updated upstream
# def logout_view(request):
#     auth_logout(request)
#     messages.success(request, "Déconnexion réussie.")
#     return redirect('connexion')

def test_email(request):
    send_mail(
        'Test Email',
        'Ceci est un test d\'envoi d\'email depuis Django.',
        'from@example.com',
        ['to@example.com'],
        fail_silently=False,
    )
    return render(request, 'authentification/email_envoye.html')



def commandes_view(request):
    return render(request, 'cuisinier/commandes.html')

def notifications_view(request):
    return render(request, 'cuisinier/notifications.html')
