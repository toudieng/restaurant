from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib import messages
from django.urls import reverse
from django.db import transaction

from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Plat, Reservation, LigneDeCommande, Commande, Utilisateur
from .forms import LoginForm, RegisterForm, AjoutPersonnelForm
from datetime import datetime, date
from django.core.mail import send_mail

from restaurant_app.paydunya_sdk.checkout import CheckoutInvoice, PaydunyaSetup
from .paydunya_config import PaydunyaSetup

from django.template.loader import get_template
from io import BytesIO
from xhtml2pdf import pisa
from datetime import datetime

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


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
                    return redirect('commandes_a_valider')
                elif role == 'Livreur':
                    return redirect('livreur')
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
                elif role == 'Livreur':
                    return redirect('livreur')
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
        date_res_str = request.POST.get('date_reservation')
        heure_res_str = request.POST.get('heure_reservation')
        nb_personnes = request.POST.get('nombre_personnes')

        try:
            date_reservation = datetime.strptime(date_res_str, '%Y-%m-%d').date()
            heure_reservation = datetime.strptime(heure_res_str, '%H:%M').time()

            date_heure_reservation = datetime.combine(date_reservation, heure_reservation)

            now = datetime.now()

            if date_heure_reservation < now:
                messages.error(request, "Vous ne pouvez pas réserver à une date ou une heure passée.")
                return redirect('faire_reservation') 

            if not nb_personnes or int(nb_personnes) <= 0:
                 messages.error(request, "Le nombre de personnes doit être supérieur à zéro.")
                 return redirect('faire_reservation')

        except ValueError:
            messages.error(request, "Format de date ou d'heure invalide.")
            return redirect('faire_reservation')

        reservation = Reservation.objects.create(
            client=request.user,
            date_reservation=date_reservation,
            heure_reservation=heure_reservation,
            nombre_personnes=nb_personnes
        )

        messages.success(request, "Votre réservation a été enregistrée. En attente de confirmation.")
        return redirect('menu')

    reservations_confirmees = Reservation.objects.filter(
        client=request.user,
        est_confirmee=True,
        date_reservation__gte=date.today() # Seulement les réservations futures ou d'aujourd'hui
    ).order_by('date_reservation', 'heure_reservation')

    context = {
        'min_date': date.today().isoformat(),
        'min_time': datetime.now().strftime('%H:%M'),
    }
    return render(request, 'client/reservation.html', context)


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
        messages.warning(request, "Votre panier est vide. Veuillez ajouter des articles avant de valider.")
        return redirect('menu')

    total = sum(float(item['prix']) * item['quantite'] for item in panier.values())

    today = date.today()
    reservations_actives = Reservation.objects.filter(
        client=request.user,
        est_confirmee=True,
        date_reservation=today # Filtre les réservations d'aujourd'hui ou futures
    ).exclude(
        # Exclut les réservations déjà liées à une commande en salle qui est 'livrée' (servie)
        commandes__mode_commande='salle',
        commandes__statut='livree' # Assurez-vous que 'livree' est le statut final pour le service en salle
    ).order_by('date_reservation', 'heure_reservation')

    context = {
        'panier': panier,
        'total': total,
        'reservations': reservations_actives, # <-- AJOUTEZ CETTE LIGNE !
        'user_phone': request.user.telephone or ''
    }
    return render(request, 'client/validation_commande.html', context)


def payer_commande(request):
    if not request.user.is_authenticated:
        return redirect('connexion')

    commande_id = request.session.get('commande_id_en_cours') # <-- Récupère l'ID de commande
    if not commande_id: # <-- Validation de l'ID
        messages.error(request, "Aucune commande en cours de traitement pour le paiement.")
        return redirect('menu')

    commande = get_object_or_404(Commande, id=commande_id, client=request.user) # <-- Récupère la commande depuis la BDD

    if commande.statut == 'payé': # <-- AJOUT
        messages.info(request, "Cette commande a déjà été payée.")
        return redirect('detail_commande', commande_id=commande.id)

    invoice = CheckoutInvoice()

    # AJOUT : Ajout des items depuis les lignes de commande de la BDD
    total = 0
    for item_line in commande.lignes.all():
        invoice.add_item(
            name=item_line.plat.nom,
            quantity=item_line.quantite,
            unit_price=float(item_line.prix_unitaire)
        )
        total += float(item_line.total_ligne) # Utilise le total_ligne de la LigneDeCommande

    invoice.total_amount = total
    invoice.description = f"Commande #{commande.id} sur L'occidental" # <-- Description plus spécifique

    # AJOUT : Ajoute l'ID de commande aux URLs de redirection
    invoice.return_url = request.build_absolute_uri(reverse('paiement_success') + f'?commande_id={commande.id}')
    invoice.cancel_url = request.build_absolute_uri(reverse('paiement_cancel') + f'?commande_id={commande.id}')

    # ... (infos client et création facture)
    if invoice.create():
        return redirect(invoice.url)
    else:
        messages.error(request, f"Erreur lors de la création de la facture PayDunya : {invoice.response_text}") # <-- Message d'erreur plus détaillé
        return render(request, 'client/erreur.html', {'message': invoice.response_text}) # <-- Gère l'erreur de manière plus propre


def paiement_success(request):
    token = request.GET.get("token")
    commande_id = request.GET.get("commande_id")

    if not commande_id:
        messages.error(request, "ID de commande manquant pour la confirmation de paiement.")
        return redirect('menu')

    commande = get_object_or_404(Commande, id=commande_id)

    if commande.statut != 'en_attente':
        messages.info(request, f"Cette commande #{commande.id} a déjà été traitée ou payée. Statut actuel : {commande.get_statut_display()}.")
        return redirect('detail_commande', commande_id=commande.id)

    invoice = CheckoutInvoice()
    confirmation = invoice.confirm(token)
    
    # Adaptez la condition ci-dessous selon la réponse réelle de PayDunya.
    # Utilisez 'status' ou 'response_code' selon ce que PayDunya renvoie pour un succès.
    if confirmation and confirmation.get("status") == "completed":
    # OU si confirmation et confirmation.get("response_code") == "00":
        try:
            with transaction.atomic():
                commande.statut = 'en_cours' 
                commande.transaction_id = token
                commande.save()

                if 'panier' in request.session:
                    del request.session['panier']
                if 'commande_id_en_cours' in request.session:
                    del request.session['commande_id_en_cours']
                request.session.modified = True 

                messages.success(request, f"Paiement réussi pour la commande #{commande.id} ! Votre commande est en cours de préparation.")
                return render(request, 'client/confirmation_commande.html', {
                    'commande': commande,
                    'paiement_ok': True,
                    'transaction': token
                })
        except Exception as e:
            messages.error(request, f"Une erreur interne est survenue après la confirmation du paiement. Veuillez contacter le support. Erreur: {e}")
            return redirect('menu')

    else:
        message = "Paiement non confirmé ou erreur inconnue."
        if confirmation:
            message = confirmation.get("response_text", message) 
        
        messages.error(request, f"Le paiement n'a pas été finalisé : {message}")
        
        try:
            commande.statut = 'annulee' 
            commande.save()
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour du statut de la commande en 'annulée'. Contactez le support. Erreur: {e}")
            
        return render(request, 'client/erreur.html', {'message': message})

@login_required
def paiement_cancel(request):
    token = request.GET.get("token")

    messages.error(request, "Le paiement a été annulé ou n'a pas pu être finalisé.")

    return redirect('menu') 


@login_required
def mes_commandes(request):
    commandes = Commande.objects.filter(client=request.user).order_by('-date_commande')
    
    context = {
        'commandes': commandes
    }
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
            messages.warning(request, "Votre panier est vide.")
            return redirect('menu')

        mode_commande = request.POST.get('mode_commande')
        telephone = request.POST.get('telephone')
        methode_paiement = request.POST.get('methode_paiement')
        
        adresse_livraison = None
        reservation = None

        if mode_commande == 'livraison':
            choix_adresse = request.POST.get('choix_adresse')
            if choix_adresse == 'manuelle':
                adresse_livraison = request.POST.get('adresse_livraison')
            elif choix_adresse == 'carte':
                # Les coordonnées viennent ici au format "lat,lng"
                coordonnees = request.POST.get('coordonnees_livraison')
                # Vous pourriez vouloir stocker les coordonnées et l'adresse textuelle séparément
                # Pour l'instant, on stocke les coordonnées ou l'adresse textuelle complète si dispo.
                adresse_livraison = request.POST.get('adresse_textuelle') or coordonnees
                if not adresse_livraison:
                    messages.error(request, "Veuillez sélectionner une adresse sur la carte ou la saisir manuellement.")
                    return redirect('validation_commande')
            
            if not adresse_livraison:
                messages.error(request, "Veuillez spécifier une adresse de livraison.")
                return redirect('validation_commande')

            if not telephone:
                messages.error(request, "Veuillez entrer un numéro de téléphone pour la livraison.")
                return redirect('validation_commande')

        elif mode_commande == 'salle':
            reservation_id = request.POST.get('reservation_id')
            if reservation_id and reservation_id != 'none':
                try:
                    # S'assurer que la réservation appartient à l'utilisateur et est confirmée
                    reservation = Reservation.objects.get(id=reservation_id, client=request.user, est_confirmee=True)
                except Reservation.DoesNotExist:
                    messages.error(request, "Réservation sélectionnée invalide ou non confirmée.")
                    return redirect('validation_commande')
            else:
                messages.error(request, "Veuillez sélectionner une réservation confirmée pour le service en salle.")
                return redirect('validation_commande')
        else:
            messages.error(request, "Mode de commande invalide.")
            return redirect('validation_commande')

        total = sum(float(item['prix']) * item['quantite'] for item in panier.values())

        try:
            with transaction.atomic():
                commande = Commande.objects.create(
                    client=request.user,
                    mode_commande=mode_commande,
                    reservation=reservation,
                    adresse_livraison=adresse_livraison,
                    telephone=telephone or request.user.telephone, 
                
                    total_paiement=total,
                    statut='en_attente',
                    moyen_paiement=methode_paiement
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

                commande.calculer_total()

                request.session['commande_id_en_cours'] = commande.id
                request.session.modified = True

                if methode_paiement == 'especes':
                    # commande.statut = 'en_attente'
                    # commande.moyen_paiement = 'espece'
                    # commande.save()
                    if 'panier' in request.session:
                        del request.session['panier']
                    request.session.modified = True
                    messages.success(request, "Votre commande a été enregistrée. Veuillez payer en espèces auprès du caissier.")
                    return render(request, 'client/confirmation_commande.html', {
                        'commande': commande,
                        'paiement_en_attente': True
                    })
                
                elif methode_paiement in ['wave', 'orange_money', 'kpay', 'carte_bancaire']:
                    return redirect('payer_commande')
                
                else:
                    return HttpResponse("Méthode de paiement non valide.", status=400)
                    return redirect('validation_commande')

        except Plat.DoesNotExist:
            messages.error(request, "Erreur : Un des plats sélectionné n'existe plus.")
            return redirect('validation_commande')
        except Exception as e:
            messages.error(request, f"Une erreur inattendue s'est produite lors de la commande : {e}")
            print(f"Erreur commande: {e}") # Pour le debug
            return redirect('validation_commande')

    messages.error(request, "Méthode de requête non autorisée.")

    return redirect('menu')

@role_required('Caissier')
def commandes_a_valider(request):
    commandes = Commande.objects.filter(
        moyen_paiement='espece',
        statut__in=['en_attente', 'en_cours']
    ).select_related('client')

    return render(request, 'caissier/commandes_a_valider.html', {'commandes': commandes})

# @role_required('Caissier')
# def valider_paiement(request, commande_id):
#     commande = get_object_or_404(Commande, id=commande_id, moyen_paiement='espece')
#     commande.statut = 'payé'
#     commande.save()
#     messages.success(request, f"Le paiement de la commande #{commande.id} a été validé.")
#     return redirect('commandes_a_valider')


@role_required('Caissier')
def valider_paiement(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id, moyen_paiement='espece')

    if commande.statut == 'en_attente':
        commande.statut = 'en_cours' 
        commande.save()
        messages.success(request, f"Le paiement de la commande #{commande.id} a été validé. La commande est maintenant 'En cours de préparation'.")
    elif commande.statut == 'en_cours':
        messages.info(request, f"La commande #{commande.id} est déjà 'En cours de préparation'. Aucune action nécessaire.")
    else:
        messages.warning(request, f"La commande #{commande.id} ne peut pas être validée car son statut est '{commande.get_statut_display()}'.")

    return redirect('commandes_a_valider')

def get_address_from_coords(latitude, longitude):
    geolocator = Nominatim(user_agent="L_Occidental_Restaurant_Facture_PDF") # User-Agent unique
    try:
        # Augmentez le timeout si vous avez des problèmes de connexion
        location = geolocator.reverse(f"{latitude}, {longitude}", timeout=10) 
        if location:
            return location.address
        else:
            return None
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"Erreur Nominaatim (timeout ou service) lors du géocodage PDF : {e}")
        return None
    except Exception as e:
        print(f"Erreur inattendue lors du géocodage inverse pour PDF : {e}")
        return None

@login_required
def generer_facture_pdf(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id)

    # Sécurité : Assurez-vous que seul le client propriétaire de la commande peut télécharger sa facture
    if request.user != commande.client and not request.user.is_staff:
        messages.error(request, "Vous n'êtes pas autorisé à accéder à cette facture.")
        return redirect('menu')

    # Vérifiez que la commande est bien payée ou traitée
    if commande.statut == 'en_attente' or commande.statut == 'annulee':
        messages.warning(request, "La facture ne peut pas être générée pour une commande en attente ou annulée.")
        return redirect('detail_commande', commande_id=commande.id)

    adresse_livraison_display = commande.adresse_livraison # Initialisation

    if commande.mode_commande == 'livraison' and commande.adresse_livraison:
        try:
            # Tente de séparer la chaîne 'lat,lon'
            lat_str, lon_str = commande.adresse_livraison.split(',')
            latitude = float(lat_str.strip())
            longitude = float(lon_str.strip())
            
            # Effectue le géocodage inverse
            resolved_address = get_address_from_coords(latitude, longitude)
            
            if resolved_address:
                adresse_livraison_display = resolved_address
            else:
                # Si la résolution échoue, affiche les coordonnées avec un message d'erreur
                adresse_livraison_display = f"Erreur de résolution d'adresse (Coordonnées: {commande.adresse_livraison})"
        except (ValueError, IndexError):
            # Si la chaîne n'est pas au format "lat,lon", c'est peut-être déjà une adresse textuelle.
            # On conserve la valeur actuelle de commande.adresse_livraison.
            pass 
        except Exception as e:
            # Pour d'autres erreurs inattendues (ex: problème réseau avec l'API)
            print(f"Erreur inattendue lors du traitement de l'adresse de livraison pour PDF: {e}")
            adresse_livraison_display = f"Erreur de résolution d'adresse (Coordonnées: {commande.adresse_livraison})"


    template_path = 'client/facture_pdf.html' 
    context = {
        'commande': commande,
        # Assurez-vous que 'lignes' est le related_name correct dans LigneDeCommande
        'lignes_commande': commande.lignes.all(), 
        'adresse_livraison_display': adresse_livraison_display,
        'date_generation': datetime.now().strftime('%d/%m/%Y %H:%M'), # Utilisez datetime.now()
    }
    template = get_template(template_path)
    html = template.render(context)

    response = BytesIO()
    pdf = pisa.CreatePDF(
        BytesIO(html.encode("UTF-8")), # Important: encodez le HTML en UTF-8
        dest=response,
        encoding='UTF-8' # Spécifiez l'encodage pour pisa
    )

    if not pdf.err:
        response_pdf = HttpResponse(response.getvalue(), content_type='application/pdf')
        response_pdf['Content-Disposition'] = f'attachment; filename="facture_commande_{commande.id}.pdf"'
        return response_pdf
    
    messages.error(request, f"Impossible de générer la facture PDF. Erreur: {pdf.err}") 
    return redirect('detail_commande', commande_id=commande.id)

def mail_reservation(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)

    if reservation.est_confirmee:
        try:
            email_context = {
                'reservation': reservation,
            }

            html_message = render_to_string('emails/confirmation_reservation_client.html', email_context)

            subject = f"Votre réservation #{reservation.id}
            to_email = reservation.client.email
            from_email = 'asdieng.elc@gmail.com'

            if to_email:
                email = EmailMessage(
                    subject,
                    html_message,
                    from_email,
                    [to_email], 
                )
                email.content_subtype = "html"
                email.send()
                messages.success(request, f"E-mail de confirmation envoyé pour la réservation #{reservation.id}.")
            else:
                messages.warning(request, f"L'e-mail du client pour la réservation #{reservation.id} est manquant. E-mail non envoyé.")

        except Exception as e:
            messages.error(request, f"Erreur lors de l'envoi de l'e-mail pour la réservation #{reservation.id}: {e}")
    else:
        messages.info(request, f"La réservation #{reservation.id} n'est pas confirmée. L'e-mail de confirmation n'a pas été envoyé.")

    return redirect('client') #


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
    commandes_salle_pretes = Commande.objects.filter(
        mode_commande='salle',
        statut='prete'
    ).select_related('client', 'reservation').prefetch_related('lignedecommande_set__plat').order_by('date_commande')

    context = {
        'commandes': commandes_salle_pretes
    }
    return render(request, 'serveur/serveur.html')

@role_required('Serveur')
def marquer_servie(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id, mode_commande='salle', statut='prete')
    if request.method == 'POST':
        commande.statut = 'livree' # Pour le service en salle, 'livree' peut signifier 'servie'
        commande.save()
        messages.success(request, f"Commande #{commande.id} marquée comme servie.")
    return redirect('serveur')

@role_required('Livreur')
def livreur_dashboard(request):
    # Commandes prêtes pour la livraison
    commandes_livraison_pretes = Commande.objects.filter(
        mode_commande='livraison',
        statut='prete'
    ).select_related('client').prefetch_related('lignedecommande_set__plat').order_by('date_commande')

    context = {
        'commandes': commandes_livraison_pretes
    }
    return render(request, 'livreur/livreur.html', context)

@role_required('Livreur')
def marquer_livree(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id, mode_commande='livraison', statut='prete')
    if request.method == 'POST':
        commande.statut = 'livree'
        commande.save()
        messages.success(request, f"Commande #{commande.id} marquée comme livrée.")
    return redirect('livreur')

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

def commandes_view(request):
    commandes = Commande.objects.all().prefetch_related('lignes')  # Optimisation

    for commande in commandes:
        commande.calculer_total()  # ✅ Met à jour le total automatiquement

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