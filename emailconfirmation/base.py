    from datetime import datetime, timedelta
from random import random

from django.conf import settings
from django.db import models, IntegrityError
from django.core.mail import send_mail
from django.core.urlresolvers import reverse, NoReverseMatch
from django.template.loader import render_to_string
from django.utils.hashcompat import sha_constructor
from django.utils.translation import gettext_lazy as _

from django.contrib.sites.models import Site

from emailconfirmation.signals import email_confirmed

class EmailAddressManager(models.Manager):
    def add_object(self, *args, **kwargs):
        try:
            obj = self.create(*args, **kwargs)
            EmailConfirmation.objects.send_confirmation(obj)
            return obj
        except IntegrityError:
            return None


class EmailAddressBase(models.Model):
    verified = models.BooleanField(default=False)
    objects = EmailAddressManager()
    
class EmailConfirmationManager(models.Manager):

    def confirm(self, confirmation_key):
        try:
            confirmation = self.get(confirmation_key=confirmation_key)
        except self.model.DoesNotExist:
            return None
        if not confirmation.key_expired():
            email_address = confirmation.email_address
            email_address.verified = True
            email_address.set_as_primary(conditional=True)
            email_address.save()
            email_confirmed.send(sender=self.model, email_address=email_address)
            return email_address

    def send_confirmation(self, email_address):
        salt = sha_constructor(str(random())).hexdigest()[:5]
        confirmation_key = sha_constructor(salt + email_address.email).hexdigest()
        current_site = Site.objects.get_current()
        # check for the url with the dotted view path
        try:
            path = reverse("emailconfirmation.views.confirm_email",
                args=[confirmation_key])
        except NoReverseMatch:
            # or get path with named urlconf instead
            path = reverse(
                "emailconfirmation_confirm_email", args=[confirmation_key])
        protocol = getattr(settings, "DEFAULT_HTTP_PROTOCOL", "http")
        activate_url = u"%s://%s%s" % (
            protocol,
            unicode(current_site.domain),
            path
        )
        context = {
#            "user": email_address.user,
            "activate_url": activate_url,
            "current_site": current_site,
            "confirmation_key": confirmation_key,
        }
        
        # add all fields from email_address to context
        fields = [x.name for x in email_address._meta.fields]
        fields.remove('verified')
        for field in fields:
            context[field] = getattr(email_address, field)
        
        subject = render_to_string(self.model._subject_template, context)
        # remove superfluous line breaks
        subject = "".join(subject.splitlines())
        message = render_to_string(self.model._message_template, context)
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email_address.email])
        return self.create(
            email_address=email_address,
            sent=datetime.now(),
            confirmation_key=confirmation_key)

    def delete_expired_confirmations(self):
        for confirmation in self.all():
            if confirmation.key_expired():
                confirmation.delete()


class EmailConfirmationBase(models.Model):
    sent = models.DateTimeField()
    confirmation_key = models.CharField(max_length=40)
    
    objects = EmailConfirmationManager()

    _message_template = "emailconfirmation/email_confirmation_message.txt"
    _subject_template = "emailconfirmation/email_confirmation_subject.txt"
    def key_expired(self):
        expiration_date = self.sent + timedelta(
            days=settings.CONFIRMATION_EXPIRE_AFTER_DAYS)
        return expiration_date <= datetime.now()
    key_expired.boolean = True


    def __unicode__(self):
        return u"confirmation for %s" % self.email_address

    class Meta:
        verbose_name = _("e-mail confirmation")
        verbose_name_plural = _("e-mail confirmations")
    
