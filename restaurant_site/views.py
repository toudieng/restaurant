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
from .utils import send_reservation_confirmation_email

from restaurant_app.paydunya_sdk.checkout import CheckoutInvoice, PaydunyaSetup
from .paydunya_config import PaydunyaSetup

from django.template.loader import get_template
from datetime import datetime

from xhtml2pdf import pisa
from io import BytesIO 

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver 

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from django.db.models import Sum, Count
from datetime import timedelta


from django.db.models import Q
from django.utils import timezone



from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import Categorie, Plat, Reservation # Importez Reservation pour la gestion des résas
from .forms import CategorieForm, PlatForm


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
    maintenant = datetime.now()
    aujourd_hui = date.today()
    semaine = aujourd_hui - timedelta(days=7)
    mois = aujourd_hui.replace(day=1)

    chiffre_jour = Commande.objects.filter(date_commande__date=aujourd_hui).aggregate(total=Sum('total_paiement'))['total'] or 0
    chiffre_semaine = Commande.objects.filter(date_commande__date__gte=semaine).aggregate(total=Sum('total_paiement'))['total'] or 0
    chiffre_mois = Commande.objects.filter(date_commande__date__gte=mois).aggregate(total=Sum('total_paiement'))['total'] or 0

    plats_populaires = Plat.objects.annotate(
        nombre_commandes=Count('lignedecommande')
    ).order_by('-nombre_commandes')[:5]

    total_tables = 20 
    tables_occupees = Reservation.objects.filter(date_reservation=aujourd_hui).count()
    taux_occupation = (tables_occupees / total_tables * 100) if total_tables > 0 else 0

    context = {
        'chiffre_jour': chiffre_jour,
        'chiffre_semaine': chiffre_semaine,
        'chiffre_mois': chiffre_mois,
        'plats_populaires': plats_populaires,
        'tables_occupees': tables_occupees,
        'total_tables': total_tables,
        'taux_occupation': taux_occupation,
    }
    return render(request, 'authentification/accueil.html', context)

@role_required('Client')
def client(request):
    return render(request, 'client/client.html')

def auth_view(request):
    login_form = LoginForm()
    register_form = RegisterForm()

    if request.method == 'POST':
        if 'login' in request.POST:
            login_form = LoginForm(request, data=request.POST)

            if login_form.is_valid():
                user = login_form.get_user()
                login(request, user)

                messages.success(request, f"Bienvenue, {user.username} !")

                role = user.role
                if role == 'Administrateur':
                    return redirect('admin_dashboard')
                elif role == 'Client':
                    return redirect('client')
                elif role == 'Serveur':
                    return redirect('serveur')
                elif role == 'Cuisinier':
                    return redirect('cuisinier_dashboard')
                elif role == 'Caissier':
                    return redirect('commandes_a_valider')
                elif role == 'Livreur':
                    return redirect('livreur')
                else:
                    return redirect('accueil')
            else:
                messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")

        elif 'register' in request.POST:
            register_form = RegisterForm(request.POST)
            if register_form.is_valid():
                user = register_form.save()
                login(request, user)
                messages.success(request, "Inscription réussie. Vous êtes maintenant connecté.")

                role = user.role
                # if role == 'Administrateur':
                #     return redirect('liste_reservations_admin')
                if role == 'Administrateur':
                    return redirect('admin_dashboard')
                elif role == 'Client':
                    return redirect('client')
                elif role == 'Serveur':
                    return redirect('serveur')
                elif role == 'Cuisinier':
                    return redirect('cuisinier_dashboard')
                elif role == 'Caissier':
                    return redirect('commandes_a_valider')
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
    search_query = request.GET.get('q', '')

    plats = Plat.objects.all()

    if search_query:
        plats = plats.filter(
            Q(nom__icontains=search_query) |
            Q(description__icontains=search_query)
        ).order_by('nom')
    else:
        plats = plats.order_by('nom')

    panier_count = sum(item['quantite'] for item in request.session.get('panier', {}).values())

    context = {
        'plats': plats,
        'panier_count': panier_count,
        'search_query': search_query,
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
        date_reservation__gte=date.today()
    ).order_by('date_reservation', 'heure_reservation')

    context = {
        'min_date': date.today().isoformat(),
        'min_time': datetime.now().strftime('%H:%M'),
    }
    return render(request, 'client/reservation.html', context)


# =============================================================
# VUES DE COMMANDE ET DE PAIEMENT
# =============================================================

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
        date_reservation=today
    ).exclude(
        commandes__mode_commande='salle',
        commandes__statut='livree'
    ).order_by('date_reservation', 'heure_reservation')

    context = {
        'panier': panier,
        'total': total,
        'reservations': reservations_actives,
        'user_phone': request.user.telephone or ''
    }
    return render(request, 'client/validation_commande.html', context)


def payer_commande(request):
    if not request.user.is_authenticated:
        return redirect('connexion')

    commande_id = request.session.get('commande_id_en_cours')
    if not commande_id:
        messages.error(request, "Aucune commande en cours de traitement pour le paiement.")
        return redirect('menu')

    commande = get_object_or_404(Commande, id=commande_id, client=request.user)

    if commande.statut == 'payé':
        messages.info(request, "Cette commande a déjà été payée.")
        return redirect('detail_commande', commande_id=commande.id)

    invoice = CheckoutInvoice()

    total = 0
    for item_line in commande.lignes.all():
        invoice.add_item(
            name=item_line.plat.nom,
            quantity=item_line.quantite,
            unit_price=float(item_line.prix_unitaire)
        )
        total += float(item_line.total_ligne)

    invoice.total_amount = total
    invoice.description = f"Commande #{commande.id} sur L'occidental"

    invoice.return_url = request.build_absolute_uri(reverse('paiement_success') + f'?commande_id={commande.id}')
    invoice.cancel_url = request.build_absolute_uri(reverse('paiement_cancel') + f'?commande_id={commande.id}')

    if invoice.create():
        return redirect(invoice.url)
    else:
        messages.error(request, f"Erreur lors de la création de la facture PayDunya : {invoice.response_text}")
        return render(request, 'client/erreur.html', {'message': invoice.response_text})


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
   
    if confirmation and confirmation.get("status") == "completed":
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
    commande = get_object_or_404(
        Commande.objects.select_related('client', 'reservation').prefetch_related('lignes__plat'),
        id=commande_id,
        client=request.user
    )

    lignes_details = []
    for ligne in commande.lignes.all():
        lignes_details.append({
            'plat': ligne.plat,
            'quantite': ligne.quantite,
            'prix_unitaire': ligne.prix_unitaire,
            'sous_total': ligne.quantite * ligne.prix_unitaire
        })

    context = {
        'commande': commande,
        'lignes_details': lignes_details,
    }
    return render(request, 'client/detail_commande.html', context)


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
                coordonnees = request.POST.get('coordonnees_livraison')
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
            print(f"Erreur commande: {e}")
            return redirect('validation_commande')

    messages.error(request, "Méthode de requête non autorisée.")

    return redirect('menu')

@role_required('Caissier')
def commandes_a_valider(request):

    commandes_en_attente = Commande.objects.filter(statut='en_attente')

    if request.method == 'POST':
        commande_id = request.POST.get('commande_id')
        if commande_id:
            try:
                commande = get_object_or_404(Commande, id=commande_id, statut='en_attente')
                commande.statut = 'en_cours'
                commande.save()
                messages.success(request, f"La commande {commande.commande_id} a été validée et est maintenant 'en cours'.")
            except Exception as e:
                messages.error(request, f"Une erreur s'est produite lors de la validation : {e}")
        return redirect('admin_valider_commandes') # Redirige pour éviter la soumission multiple du formulaire

    context = {
        'commandes_en_attente': commandes_en_attente
    }

    return render(request, 'caissier/commandes_a_valider.html', context)


@role_required('Caissier')
def valider_paiement(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id, moyen_paiement='espece')

    if commande.statut == 'en_attente':
        commande.statut = 'en_cours' 
        commande.save()
        messages.success(request, f"Le paiement de la commande #{commande.id} a été validé. La commande est maintenant 'En cours de préparation'.")

        messages.info(request, 
                      f"Cliquez <a href=\"{reverse('generer_facture_pdf', args=[commande.id])}\" target=\"_blank\" class=\"alert-link\">ici</a> pour générer la facture PDF de la commande #{commande.id}.")

    elif commande.statut == 'en_cours':
        messages.info(request, f"La commande #{commande.id} est déjà 'En cours de préparation'. Aucune action nécessaire.")
    else:
        messages.warning(request, f"La commande #{commande.id} ne peut pas être validée car son statut est '{commande.get_statut_display()}'.")

    return redirect('commandes_a_valider')


def get_address_from_coords(latitude, longitude):
    geolocator = Nominatim(user_agent="L_Occidental_Restaurant_Facture_PDF")
    try:
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

    if request.user != commande.client and not request.user.is_staff:
        messages.error(request, "Vous n'êtes pas autorisé à accéder à cette facture.")
        return redirect('menu')

    if commande.statut == 'en_attente' or commande.statut == 'annulee':
        messages.warning(request, "La facture ne peut pas être générée pour une commande en attente ou annulée.")
        return redirect('detail_commande', commande_id=commande.id)

    adresse_livraison_display = commande.adresse_livraison

    if commande.mode_commande == 'livraison' and commande.adresse_livraison:
        try:
            lat_str, lon_str = commande.adresse_livraison.split(',')
            latitude = float(lat_str.strip())
            longitude = float(lon_str.strip())
            
            resolved_address = get_address_from_coords(latitude, longitude)
            
            if resolved_address:
                adresse_livraison_display = resolved_address
            else:
                adresse_livraison_display = f"Erreur de résolution d'adresse (Coordonnées: {commande.adresse_livraison})"
        except (ValueError, IndexError):
            pass
        except Exception as e:
            print(f"Erreur inattendue lors du traitement de l'adresse de livraison pour PDF: {e}")
            adresse_livraison_display = f"Erreur de résolution d'adresse (Coordonnées: {commande.adresse_livraison})"


    template_path = 'client/facture_pdf.html'
    context = {
        'commande': commande,
        'lignes_commande': commande.lignes.all(),
        'adresse_livraison_display': adresse_livraison_display,
        'date_generation': datetime.now().strftime('%d/%m/%Y %H:%M'),
    }
    template = get_template(template_path)
    html = template.render(context)

    response = BytesIO()
    pdf = pisa.CreatePDF(
        BytesIO(html.encode("UTF-8")),
        dest=response,
        encoding='UTF-8'
    )

    if not pdf.err:
        response_pdf = HttpResponse(response.getvalue(), content_type='application/pdf')
        response_pdf['Content-Disposition'] = f'attachment; filename="facture_commande_{commande.id}.pdf"'
        return response_pdf

    messages.error(request, f"Impossible de générer la facture PDF. Erreur: {pdf.err}")
    return redirect('detail_commande', commande_id=commande.id)

@login_required
def liste_reservations_admin(request):
    """
    Affiche un tableau de bord des réservations pour l'administrateur.
    Filtre les réservations non confirmées et à venir.
    """
    reservations_a_confirmer = Reservation.objects.filter(
        est_confirmee=False,
        date_reservation__gte=timezone.now().date()
    ).order_by('date_reservation', 'heure_reservation')

    context = {
        'reservations': reservations_a_confirmer,
    }
    return render(request, 'admin/admin_dashboard_reservations.html', context)


@login_required
def confirmer_reservation_par_admin(request, reservation_id):
    """
    Confirme une réservation et envoie un e-mail de confirmation au client.
    """
    reservation = get_object_or_404(Reservation, id=reservation_id)

    if request.method == 'POST':
        if not reservation.est_confirmee:
            reservation.est_confirmee = True
            reservation.date_confirmation = timezone.now()
            reservation.confirme_par = request.user
            reservation.save()

            messages.success(request, f"La réservation #{reservation.id} a été confirmée avec succès.")

            send_reservation_confirmation_email(request, reservation)

        else:
            messages.info(request, f"La réservation #{reservation.id} est déjà confirmée.")

    return redirect('liste_reservations_admin')

@login_required
def annuler_reservation_par_admin(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)

    if request.method == 'POST':
        if not reservation.est_confirmee:
            reservation.statut = 'annulee'
            reservation.save()
            messages.success(request, f"La réservation #{reservation.id} a été annulée avec succès.")
        else:
            messages.warning(request, f"La réservation #{reservation.id} est déjà confirmée et ne peut pas être annulée directement depuis ici.")
    else:
        messages.error(request, "Requête non valide.")

    return redirect('liste_reservations_admin')


# =============================================================
# VUES D'ADMINISTRATION
# =============================================================

@role_required('Serveur')
def serveur_dashboard(request):
    commandes_salle_pretes = Commande.objects.filter(
        mode_commande='salle',
        statut='prete'
    ).select_related('client', 'reservation').prefetch_related('lignedecommande_set__plat').order_by('date_commande')

    context = {
        'commandes': commandes_salle_pretes
    }
    return render(request, 'serveur/serveur.html', context)

@role_required('Serveur')
def marquer_servie(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id, mode_commande='salle', statut='prete')
    if request.method == 'POST':
        commande.statut = 'livree'
        commande.save()
        messages.success(request, f"Commande #{commande.id} marquée comme servie.")
    return redirect('serveur')

@role_required('Livreur')
def livreur_dashboard(request):
    commandes_livraison_pretes = Commande.objects.filter(
        mode_commande='livraison',
        statut='prete'
    ).select_related('client').prefetch_related('lignes__plat').order_by('date_commande')

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

@role_required('Cuisinier')
def cuisinier_dashboard(request):
    commandes = Commande.objects.filter(
        statut='en_cours'
    ).prefetch_related('lignes__plat').order_by('date_commande')
    for commande in commandes:
        commande.calculer_total()
    return render(request, 'cuisinier.html', {'commandes': commandes})



@login_required
def changer_statut_commande(request, id):
    if request.method == "POST":
        commande = get_object_or_404(Commande, id=id)
        nouveau_statut = request.POST.get("statut")
        if nouveau_statut == 'prete':
            commande.statut = 'prete'
            commande.save()
    return redirect('commandes')


@receiver([post_save, post_delete], sender=LigneDeCommande)
def mettre_a_jour_total_commande(sender, instance, **kwargs):
    instance.commande.calculer_total()






# Fonction pour vérifier si l'utilisateur est un administrateur
def is_admin(user):
    return user.is_authenticated and user.role == 'Administrateur'

# --- Vues pour la gestion des Catégories ---

@user_passes_test(is_admin)
def categorie_list(request):
    categories = Categorie.objects.all()
    return render(request, 'admin_panel/categories/list.html', {'categories': categories})

@user_passes_test(is_admin)
def categorie_create(request):
    if request.method == 'POST':
        form = CategorieForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin_categorie_list')
    else:
        form = CategorieForm()
    return render(request, 'admin_panel/categories/create.html', {'form': form})

@user_passes_test(is_admin)
def categorie_update(request, pk):
    categorie = get_object_or_404(Categorie, pk=pk)
    if request.method == 'POST':
        form = CategorieForm(request.POST, instance=categorie)
        if form.is_valid():
            form.save()
            return redirect('admin_categorie_list')
    else:
        form = CategorieForm(instance=categorie)
    return render(request, 'admin_panel/categories/update.html', {'form': form, 'categorie': categorie})

@user_passes_test(is_admin)
def categorie_delete(request, pk):
    categorie = get_object_or_404(Categorie, pk=pk)
    if request.method == 'POST':
        categorie.delete()
        return redirect('admin_categorie_list')
    return render(request, 'admin_panel/categories/confirm_delete.html', {'categorie': categorie})

# --- Vues pour la gestion des Plats ---

@user_passes_test(is_admin)
def plat_list(request):
    plats = Plat.objects.all()
    return render(request, 'admin_panel/plats/list.html', {'plats': plats})

@user_passes_test(is_admin)
def plat_create(request):
    if request.method == 'POST':
        # N'oubliez pas request.FILES pour les images
        form = PlatForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('admin_plat_list')
    else:
        form = PlatForm()
    return render(request, 'admin_panel/plats/create.html', {'form': form})

@user_passes_test(is_admin)
def plat_update(request, pk):
    plat = get_object_or_404(Plat, pk=pk)
    if request.method == 'POST':
        form = PlatForm(request.POST, request.FILES, instance=plat) # N'oubliez pas request.FILES
        if form.is_valid():
            form.save()
            return redirect('admin_plat_list')
    else:
        form = PlatForm(instance=plat)
    return render(request, 'admin_panel/plats/update.html', {'form': form, 'plat': plat})

@user_passes_test(is_admin)
def plat_delete(request, pk):
    plat = get_object_or_404(Plat, pk=pk)
    if request.method == 'POST':
        plat.delete()
        return redirect('admin_plat_list')
    return render(request, 'admin_panel/plats/confirm_delete.html', {'plat': plat})

@user_passes_test(is_admin)
def plat_toggle_status(request, pk):
    # Action rapide pour marquer "épuisé" ou "spécialité du jour"
    if request.method == 'POST':
        plat = get_object_or_404(Plat, pk=pk)
        if 'toggle_epuise' in request.POST:
            plat.est_epuise = not plat.est_epuise
        elif 'toggle_specialite' in request.POST:
            plat.specialite_du_jour = not plat.specialite_du_jour
        plat.save()
    return redirect('admin_plat_list')

# --- Vues pour la gestion des Réservations (extension de l'existant) ---

@user_passes_test(is_admin)
def reservation_list(request):
    reservations = Reservation.objects.all().order_by('-created_at') # Les plus récentes en premier
    return render(request, 'admin_panel/reservations/list.html', {'reservations': reservations})

@user_passes_test(is_admin)
def reservation_toggle_confirmation(request, pk):
    if request.method == 'POST':
        reservation = get_object_or_404(Reservation, pk=pk)
        reservation.est_confirmee = not reservation.est_confirmee
        reservation.save()
    return redirect('admin_reservation_list') # Redirige vers la liste des réservations