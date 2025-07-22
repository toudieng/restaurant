from django.db import models
from django.contrib.auth.models import AbstractUser

class Utilisateur(AbstractUser):
    ADMINISTRATEUR = 'administrateur'
    CLIENT = 'client'
    SERVEUR = 'serveur'
    CUISINIER = 'cuisinier'
    CAISSIER = 'caissier'

    ROLE_CHOICES = [
        (ADMINISTRATEUR, 'Administrateur'),
        (CLIENT, 'Client'),
        (SERVEUR, 'Serveur'),
        (CUISINIER, 'Cuisinier'),
        (CAISSIER, 'Caissier'),
    ]

    class Meta:
        db_table = 'Utilisateur'
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=CLIENT)

    def __str__(self):
        return f"{self.username} - {self.role}"


class Categorie(models.Model):
    id = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=100)

    class Meta:
        ordering = ['nom']
        db_table = 'Categorie'
        verbose_name = 'Catégorie'
        verbose_name_plural = 'Catégories'

    def __str__(self):
        return f"{self.nom}"
    

class Plat(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField()
    prix = models.DecimalField(max_digits=6, decimal_places=2)
    image = models.ImageField(upload_to='plats/', null=True, blank=True) 
    allergenes = models.CharField(max_length=255, blank=True)
    est_epuise = models.BooleanField(default=False) 
    categorie = models.ForeignKey(Categorie, on_delete=models.CASCADE) 
    specialite_du_jour = models.BooleanField(default=False)

    class Meta :
        ordering = ['nom'] # Trie par nom par défaut
        db_table = 'Plats' 
        verbose_name = 'Plat'
        verbose_name_plural = 'Plats'

    def __str__(self):
        status = "(Épuisé)" if self.est_epuise else ""
        return f"{self.nom} {self.prix} {self.description} {self.image} {self.allergenes} {self.est_epuise} {self.specialite_du_jour}"    
