from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static

urlpatterns = [
    # URLs d'authentification
    path('', views.accueil_view, name='accueil'),
    path('connexion/', views.auth_view, name='connexion'),
    path('register/', views.auth_view, name='register'),

    path('logout/', views.logout_view, name='logout'),
    path('menu/', views.menu, name='menu'),
    path('client/', views.client, name='client'),

    #path('commandes/', views.cuisinier_dashboard, name='commandes'),
    path('changer-statut-commande/<int:id>/', views.changer_statut_commande, name='changer_statut_commande'),
    path('cuisinier/dashboard', views.cuisinier_dashboard, name='cuisinier_dashboard'),



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
    #path('caissier/valider/<int:commande_id>/', views.valider_paiement, name='valider_paiement'),
    path('caissier/commandes/<int:commande_id>/valider-paiement/', views.valider_paiement, name='valider_paiement'),

    path('serveur/dashboard/', views.serveur_dashboard, name='serveur'),
    path('serveur/marquer_servie/<int:commande_id>/', views.marquer_servie, name='marquer_servie'),

    path('livreur/dashboard/', views.livreur_dashboard, name='livreur'),
    path('livreur/marquer_livree/<int:commande_id>/', views.marquer_livree, name='marquer_livree'),

    path('commande/<int:commande_id>/facture/pdf/', views.generer_facture_pdf, name='generer_facture_pdf'),

    # path('admin-dashboard/reservations/', views.liste_reservations_admin, name='liste_reservations_admin'),
    # path('admin-dashboard/reservations/confirmer/<int:reservation_id>/', views.confirmer_reservation_par_admin, name='confirmer_reservation_par_admin'),
    # path('admin/reservations/annuler/<int:reservation_id>/', views.annuler_reservation_par_admin, name='annuler_reservation_par_admin'),

    path('admin_panel/', views.categorie_list, name='admin_dashboard'),
    path('admin_panel/categories/', views.categorie_list, name='admin_categorie_list'),
    path('admin_panel/categories/add/', views.categorie_create, name='admin_categorie_create'),
    path('admin_panel/categories/edit/<int:pk>/', views.categorie_update, name='admin_categorie_update'),
    path('admin_panel/categories/delete/<int:pk>/', views.categorie_delete, name='admin_categorie_delete'),

    # URLs pour les Plats
    path('admin_panel/plats/', views.plat_list, name='admin_plat_list'),
    path('admin_panel/plats/add/', views.plat_create, name='admin_plat_create'),
    path('admin_panel/plats/edit/<int:pk>/', views.plat_update, name='admin_plat_update'),
    path('admin_panel/plats/delete/<int:pk>/', views.plat_delete, name='admin_plat_delete'),
    path('admin_panel/plats/toggle-status/<int:pk>/', views.plat_toggle_status, name='admin_plat_toggle_status'),

    # URLs pour les Réservations (extension)
    path('admin_panel/reservations/', views.reservation_list, name='admin_reservation_list'),
    path('admin_panel/reservations/toggle-confirmation/<int:pk>/', views.reservation_toggle_confirmation, name='admin_reservation_toggle_confirmation'),

]

