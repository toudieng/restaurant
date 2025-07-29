from django.apps import AppConfig


class RestaurantSiteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'restaurant_site'
    def ready(self):
        import restaurant_site.signals


