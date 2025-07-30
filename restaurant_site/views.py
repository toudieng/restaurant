from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib import messages
from django.urls import reverse
from django.db import transaction

from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Plat, Reservation, LigneDeCommande, Commande, Utilisateur
from .forms import LoginForm, RegisterForm, AjoutPersonnelForm
from django.core.mail import send_mail
from django.views.decorators.http import require_POST
from restaurant_app.paydunya_sdk.checkout import CheckoutInvoice, PaydunyaSetup
from .paydunya_config import PaydunyaSetup
from django.shortcuts import render, redirect

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count
from .models import Commande, LigneDeCommande, Plat

from decimal import Decimal


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
                    return redirect('commandes')
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
                    return redirect('commandes')
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

# MODE_TEST_PAIEMENT = True

# def handle_mock_payment(request, commande):
#     print(f"Mode de test activé : Paiement simulé pour la commande #{commande.id}.")
#     commande.statut = 'en_cours'
#     commande.save()
    
#     if 'panier' in request.session:
#         del request.session['panier']
    
#     return render(request, 'client/confirmation_commande.html', {'commande': commande})


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

def payer_commande(request):
    if not request.user.is_authenticated:
        return redirect('connexion')

    panier = request.session.get('panier', {})
    if not panier:
        messages.error(request, "Votre panier est vide.")
        return redirect('menu')

    invoice = CheckoutInvoice()

    # 🛒 Ajout dynamique du panier
    total = 0
    for plat_id, item in panier.items():
        prix = float(item['prix'])
        quantite = int(item['quantite'])
        invoice.add_item(
            name=item['nom'],
            quantity=quantite,
            unit_price=prix
        )
        total += prix * quantite

    invoice.total_amount = total
    invoice.description = "Commande sur L'occidental"

    # 🔁 URLs de redirection
    invoice.return_url = request.build_absolute_uri('/commande/success/')
    invoice.cancel_url = request.build_absolute_uri('/commande/cancel/')

    # 👤 Infos client à inclure dans custom_data du payload
    invoice.customer_name = request.user.get_full_name() or request.user.username
    invoice.customer_email = request.user.email
    invoice.customer_phone_number = request.user.telephone  # Assure-toi que ce champ est bien dans ton modèle

    # 📤 Création de la facture et redirection vers PayDunya
    if invoice.create():
        return redirect(invoice.url)
    else:
        return render(request, 'client/erreur.html', {'message': invoice.response_text})


def paiement_success(request):
    token = request.GET.get("token")
    invoice = CheckoutInvoice()
    confirmation = invoice.confirm(token)  # Nouvelle méthode confirm(token)

    if confirmation.get("status") == "completed":
        panier = request.session.get('panier', {})
        if not panier:
            return render(request, 'client/erreur.html', {'message': "Aucun panier trouvé."})

        # Création de la commande
        commande = Commande.objects.create(
            client=request.user,
            total_paiement=invoice.total_amount,  # ou confirmation.get("amount") ?
            statut='payé',
            transaction_id=token  # utile pour suivi
        )

        for plat_id, item in panier.items():
            plat = Plat.objects.get(id=plat_id)
            LigneDeCommande.objects.create(
                commande=commande,
                plat=plat,
                quantite=item['quantite'],
                prix_unitaire=item['prix']
            )

        # 🔥 Calculer et sauvegarder le total de la commande
        commande.calculer_total()

        # Vider le panier
        del request.session['panier']
        request.session.modified = True

        return render(request, 'client/confirmation_commande.html', {
            'commande': commande,
            'transaction': token
        })
    else:
        message = confirmation.get("message", "Paiement non confirmé.")
        return render(request, 'client/erreur.html', {'message': message})


@login_required
def mes_commandes(request):
    commandes = Commande.objects.filter(client=request.user).order_by('-date')
    return render(request, 'client/mes_commandes.html', {'commandes': commandes})

@login_required
def detail_commande(request, commande_id):
    commande = Commande.objects.get(id=commande_id, client=request.user)
    lignes = commande.lignecommande_set.select_related('plat')
    return render(request, 'client/detail_commande.html', {'commande': commande, 'lignes': lignes})


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
                    return redirect('payer_commande')
                
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


def role_required(role):
    def decorator(view_func):
        return user_passes_test(lambda u: u.is_authenticated and u.role == role)(view_func)
    return decorator


@role_required('Serveur')
def serveur_dashboard(request):
    return render(request, 'serveur.html')

@role_required('Cuisinier')
def cuisinier_dashboard(request):
    return render(request, 'cuisinier.html')

@role_required('Caissier')
def caissier_dashboard(request):
    return render(request, 'caissier.html')


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



# def commandes_view(request):
#     print("✅ Vue cuisinier appelée")
#     # Récupérer toutes les commandes avec leurs lignes associées
#     commandes = Commande.objects.prefetch_related('lignes__plat').select_related('client')


#     return render(request, 'cuisinier.html', {
#         'commandes': commandes
#     })

@login_required
def commandes_view(request):
    commandes = Commande.objects.filter(statut__in=['en_attente', 'en_cours']).prefetch_related('lignes', 'lignes__plat', 'client')
    for commande in commandes:
        commande.calculer_total()
    return render(request, 'cuisinier.html', {'commandes': commandes})

@login_required
def changer_statut_commande(request, commande_id):
    if request.method == 'POST':
        commande = get_object_or_404(Commande, id=commande_id)
        nouveau_statut = request.POST.get('statut')
        if nouveau_statut in ['en_attente', 'en_cours', 'prete', 'livree', 'annulee']:
            commande.statut = nouveau_statut
            commande.save()
    return redirect('commandes')


@receiver([post_save, post_delete], sender=LigneDeCommande)
def mettre_a_jour_total_commande(sender, instance, **kwargs):
    instance.commande.calculer_total()



def statistique(request):
    now = timezone.now()

    # ✅ Simulation temporaire des commandes
    Commande.objects.all().delete()  # Supprime toutes les commandes existantes (pour test)
    Commande.objects.create(date_commande=now, total_paiement=Decimal('125.50'))
    Commande.objects.create(date_commande=now - timedelta(days=1), total_paiement=Decimal('80.00'))
    Commande.objects.create(date_commande=now - timedelta(days=6), total_paiement=Decimal('60.00'))
    Commande.objects.create(date_commande=now - timedelta(days=30), total_paiement=Decimal('150.00'))

    # ✅ Chiffre d'affaires
    chiffre_jour = Commande.objects.filter(date_commande__date=now.date()).aggregate(Sum('total_paiement'))['total_paiement__sum'] or 0
    chiffre_semaine = Commande.objects.filter(date_commande__gte=now - timedelta(days=7)).aggregate(Sum('total_paiement'))['total_paiement__sum'] or 0
    chiffre_mois = Commande.objects.filter(date_commande__month=now.month).aggregate(Sum('total_paiement'))['total_paiement__sum'] or 0

    # ✅ Plats populaires simulés (si tu n’as pas encore de données LigneDeCommande)
    plats_populaires = (
        Plat.objects.annotate(nombre_commandes=Count('lignedecommande'))
        .order_by('-nombre_commandes')[:5]
    )

    # ✅ Simulation des tables
    total_tables = 40
    tables_occupees = 10
    taux_occupation = (tables_occupees / total_tables) * 100

    context = {
        "chiffre_jour": chiffre_jour,
        "chiffre_semaine": chiffre_semaine,
        "chiffre_mois": chiffre_mois,
        "plats_populaires": plats_populaires,
        "taux_occupation": round(taux_occupation, 1),
        "tables_occupees": tables_occupees,
        "total_tables": total_tables,
    }

    return render(request, "accueil.html", context)