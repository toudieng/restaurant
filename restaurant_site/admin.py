from django.contrib import admin
from .models import Categorie, Plat
from .models import Utilisateur, Commande, LigneDeCommande, Reservation
from django.contrib.auth.admin import UserAdmin


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom')
    search_fields = ('nom',)

@admin.register(Plat)
class PlatAdmin(admin.ModelAdmin):
    list_display = ('nom', 'categorie', 'prix', 'est_epuise', 'specialite_du_jour')
    list_filter = ('categorie', 'est_epuise', 'specialite_du_jour')
    search_fields = ('nom', 'description','allergenes')
    list_editable = ('est_epuise', 'specialite_du_jour')


class UtilisateurAdmin(UserAdmin):
    model = Utilisateur
    list_display = UserAdmin.list_display + ('role',)
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role',)}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (('Rôle', {'fields': ('role',)}),)
    )

admin.site.register(Utilisateur, UtilisateurAdmin)    

class LigneDeCommandeInline(admin.TabularInline):
    model = LigneDeCommande
    extra = 0 # Ne pas afficher de lignes vides par défaut
    readonly_fields = ['prix_unitaire', 'total_ligne']

admin.site.register(LigneDeCommande)


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'client_id', 'date_commande', 'statut', 'total_paiement')
    list_filter = ('statut', 'date_commande')
    search_fields = ('client__username', 'id')
    readonly_fields = ['date_commande', 'total_paiement']
    inlines = [LigneDeCommandeInline]

    # Méthode pour mettre à jour le total quand la commande est enregistrée
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.calculer_total()

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'client_id', 'date_reservation', 'heure_reservation', 'nombre_personnes', 'est_confirmee', 'created_at')
    list_filter = ('est_confirmee',)
    search_fields = ('client__username', 'date_reservation')
    list_editable = ('est_confirmee',)