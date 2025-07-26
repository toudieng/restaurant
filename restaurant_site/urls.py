from django.urls import path
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('', views.accueil_view, name='accueil'),
    path('connexion/', views.auth_view, name='connexion'),
    path('login/', views.auth_view, name='login'),
    path('register/', views.auth_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    

    path('client/', views.client_dashboard, name='client'),
     path('menu', views.menu, name='menu'),
    path('serveur/', views.serveur_dashboard, name='serveur'),
    path('cuisinier/', views.cuisinier_dashboard, name='cuisinier'),
    path('caissier/', views.caissier_dashboard, name='caissier'),

    path('renitialiser_password/', auth_views.PasswordResetView.as_view(
        template_name='authentification/renitialiser_password.html'), name='password_reset'),
    path('renitialisation_password_terminer/', auth_views.PasswordResetDoneView.as_view(
        template_name='authentification/renitialisation_password_terminer.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='authentification/renitialisation_password_confirmer.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='authentification/renitialisation_password_complet.html'), name='password_reset_complete'),

    path('test-email/', views.test_email, name='test_email'),
]