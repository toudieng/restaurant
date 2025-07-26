from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from restaurant_site.views import auth_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('restaurant_site.urls')),
    path('accounts/login/', auth_view),

] 

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)