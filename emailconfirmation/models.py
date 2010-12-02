from django.db import models
from django.contrib.auth.models import User

from emailconfirmation import base

# this code based in-part on django-registration


class EmailAddressManager(base.EmailAddressManager):
    def get_primary(self, user):
        try:
            return self.get(user=user, primary=True)
        except EmailAddress.DoesNotExist:
            return None

    def get_users_for(self, email):
        """
        returns a list of users with the given email.
        """
        # this is a list rather than a generator because we probably want to
        # do a len() on it right away
        return [address.user for address in EmailAddress.objects.filter(
            verified=True, email=email)]

class EmailAddress(base.EmailAddressBase):
    user = models.ForeignKey(User)
    primary = models.BooleanField(default=False)
    email = models.EmailField()


    def set_as_primary(self, conditional=False):
        old_primary = EmailAddress.objects.get_primary(self.user)
        if old_primary:
            if conditional:
                return False
            old_primary.primary = False
            old_primary.save()
        self.primary = True
        self.save()
        self.user.email = self.email
        self.user.save()
        return True

    def __unicode__(self):
        return u"%s (%s)" % (self.email, self.user)

    class Meta:
        verbose_name = _("e-mail address")
        verbose_name_plural = _("e-mail addresses")
        unique_together = (
            ("user", "email"),
        )


class EmailConfirmation(base.EmailConfirmationBase):
    email_address = models.ForeignKey(EmailAddress)



