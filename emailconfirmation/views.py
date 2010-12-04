from django.shortcuts import render_to_response
from django.template import RequestContext
from django.db import models
#from emailconfirmation.models import EmailConfirmation

def confirm_email(request, confirmation_key):
    apps = models.get_apps()
    for app in apps:
        try:
            EmailConfirmation = getattr(app, 'EmailConfirmation')
            break
        except:
            pass

    confirmation_key = confirmation_key.lower()
    email_address = EmailConfirmation.objects.confirm_email(confirmation_key)
    return render_to_response("emailconfirmation/confirm_email.html", {
        "email_address": email_address,
    }, context_instance=RequestContext(request))
