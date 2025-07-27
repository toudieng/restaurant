from django.db import models
from django.contrib.auth.models import AbstractUser

class Utilisateur(AbstractUser):
    ADMINISTRATEUR = 'Administrateur'
    CLIENT = 'Client'
    SERVEUR = 'Serveur'
    CUISINIER = 'Cuisinier'
    CAISSIER = 'Caissier'

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


from django.db import models
from django.contrib.auth.models import User # Assurez-vous d'importer le bon modèle utilisateur
# from .models import Réservation # Assurez-vous d'importer le modèle de réservation si vous l'avez dans le même fichier

class Commande(models.Model):
    STATUT_COMMANDE = (
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours de préparation'),
        ('prete', 'Prête'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    )
    MODE_COMMANDE = (
        ('salle', 'Service en salle'),
        ('livraison', 'Livraison'),
    )
    
    # L'identifiant de l'utilisateur qui a passé la commande
    client = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='commandes')
    
    # Le nouveau champ de lien vers la réservation
    reservation = models.ForeignKey('Reservation', on_delete=models.SET_NULL, null=True, blank=True, related_name='commandes')
    
    # Informations sur la commande
    date_commande = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=20, choices=STATUT_COMMANDE, default='en_attente')
    total_paiement = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Nouveaux champs pour la gestion des options
    mode_commande = models.CharField(max_length=20, choices=MODE_COMMANDE, default='salle')
    adresse_livraison = models.CharField(max_length=255, blank=True, null=True)
    
    # ... (Vos méthodes ou champs supplémentaires)

    class Meta:
        ordering = ['-date_commande'] # Trie par date de commande la plus récente
        verbose_name = 'Commande'
        verbose_name_plural = 'Commandes'

    def __str__(self):
        return f"Commande #{self.pk} par {self.client.username}"
    
    def calculer_total(self):
        """
        Calcule le total de la commande en sommant le prix de chaque ligne.
        """
        total = sum(item.total_ligne for item in self.lignes.all())
        self.total_paiement = total
        self.save()
        return total


# Nouveau modèle pour les lignes de commande
class LigneDeCommande(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name='lignes')
    plat = models.ForeignKey(Plat, on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField(default=1)
    prix_unitaire = models.DecimalField(max_digits=6, decimal_places=2)
    total_ligne = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Ligne de commande'
        verbose_name_plural = 'Lignes de commande'

    def __str__(self):
        return f"{self.quantite} x {self.plat.nom}"
    
    # Méthode pour calculer le total de la ligne
    def save(self, *args, **kwargs):
        self.total_ligne = self.prix_unitaire * self.quantite
        super().save(*args, **kwargs)

class Reservation(models.Model):
    client = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='reservations')
    date_reservation = models.DateField()
    heure_reservation = models.TimeField()
    nombre_personnes = models.PositiveIntegerField()
    est_confirmee = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['date_reservation', 'heure_reservation']
        verbose_name = 'Réservation'
        verbose_name_plural = 'Réservations'

    def __str__(self):
        return f"Réservation pour {self.client.username} le {self.date_reservation} à {self.heure_reservation}"