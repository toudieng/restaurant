from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # URLs d'authentification
    path('', views.accueil_view, name='accueil'),
    path('connexion/', views.auth_view, name='connexion'),
    path('register/', views.auth_view, name='register'),

    path('logout/', views.logout_view, name='logout'),
    path('menu/', views.menu, name='menu'),
    path('client/', views.client, name='client'),
    path('cuisinier/', views.cuisinier_dashboard, name='cuisinier'),

    path('commandes/', views.commandes_view, name='commandes'),

    path('renitialiser_password/', auth_views.PasswordResetView.as_view(
        template_name='authentification/renitialiser_password.html'), name='password_reset'),
    path('renitialisation_password_terminer/', auth_views.PasswordResetDoneView.as_view(
        template_name='authentification/renitialisation_password_terminer.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='authentification/renitialisation_password_confirmer.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='authentification/renitialisation_password_complet.html'), name='password_reset_complete'),
        
    path('test-email/', views.test_email, name='test_email'),

    path('panier/', views.voir_panier, name='panier'),
    path('panier/ajouter/<int:plat_id>/', views.ajouter_au_panier, name='ajouter_au_panier'),
    path('panier/modifier/<int:plat_id>/', views.modifier_quantite, name='modifier_quantite'),
    path('panier/supprimer/<int:plat_id>/', views.supprimer_du_panier, name='supprimer_du_panier'),
    
    # URLs pour la commande et la réservation
    path('commande/valider/', views.validation_commande, name='validation_commande'),
    path('commande/traitement/', views.traitement_commande, name='traitement_commande'),
    path('reservation/', views.faire_reservation, name='faire_reservation'),
    path('commande/paiement/', views.payer_commande, name='payer_commande'),
    path('commande/success/', views.paiement_success, name='paiement_success'),
    path('commande/paiement/cancel/', views.paiement_cancel, name='paiement_cancel'),
    path('mes-commandes/', views.mes_commandes, name='mes_commandes'),
    path('commande/<int:commande_id>/', views.detail_commande, name='detail_commande'),

    path('caissier/commandes/', views.commandes_a_valider, name='commandes_a_valider'),
    path('caissier/valider/<int:commande_id>/', views.valider_paiement, name='valider_paiement'),

    path('serveur/dashboard/', views.serveur_dashboard, name='serveur'), # Nouvelle URL
    path('serveur/marquer_servie/<int:commande_id>/', views.marquer_servie, name='marquer_servie'),

    path('livreur/dashboard/', views.livreur_dashboard, name='livreur'), # Nouvelle URL
    path('livreur/marquer_livree/<int:commande_id>/', views.marquer_livree, name='marquer_livree'),

    path('commande/<int:commande_id>/facture/pdf/', views.generer_facture_pdf, name='generer_facture_pdf'),

]

