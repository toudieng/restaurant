from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib import messages

def send_reservation_confirmation_email(request, reservation):
    try:
        if reservation.client.email:
            email_context = {
                'reservation': reservation,
            }
            html_message = render_to_string('emails/confirmation_commande_client.html', email_context)

            subject = f"Votre réservation #{reservation.id} à L'Occidental est confirmée !"
            to_email = reservation.client.email
            from_email = settings.DEFAULT_FROM_EMAIL

            email = EmailMessage(
                subject,
                html_message,
                from_email,
                [to_email],
            )
            email.content_subtype = "html"
            email.send()
            if request:
                messages.success(request, f"E-mail de confirmation envoyé pour la réservation #{reservation.id}.")
        else:
            if request:
                messages.warning(request, f"L'e-mail du client pour la réservation #{reservation.id} est manquant. E-mail non envoyé.")

    except Exception as e:
        if request:
            messages.error(request, f"Erreur lors de l'envoi de l'e-mail pour la réservation #{reservation.id}: {e}")
        
        print(f"DEBUG: Erreur lors de l'envoi d'e-mail: {e}")