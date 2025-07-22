from django.contrib import admin
from .models import Categorie, Plat
from .models import Utilisateur
from django.contrib.auth.admin import UserAdmin


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom')
    earch_fields = ('nom',)

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
# Register your models here.
