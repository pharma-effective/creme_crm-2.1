# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2015  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

import logging
# import warnings

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db.models import (ForeignKey, CharField, TextField, ManyToManyField,
        DateField, EmailField, URLField, SET_NULL)
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext_lazy

from creme.creme_core.core.exceptions import SpecificProtectedError
from creme.creme_core.models import CremeEntity, Language  # CremeEntityManager
from creme.creme_core.models.fields import PhoneField
from creme.creme_core.utils import update_model_instance

from creme.media_managers.models import Image

from ..import get_contact_model, get_organisation_model
from ..constants import REL_OBJ_EMPLOYED_BY
from .base import PersonWithAddressesMixin
from .other_models import Civility, Position, Sector


logger = logging.getLogger(__name__)


class AbstractContact(CremeEntity, PersonWithAddressesMixin):
    civility    = ForeignKey(Civility, verbose_name=_(u'Civility'),
                             blank=True, null=True, on_delete=SET_NULL,
                            )
    last_name   = CharField(_(u'Last name'), max_length=100)  # NB: same max_length than CremeUser.last_name
    first_name  = CharField(_(u'First name'), max_length=100, blank=True, null=True)  # NB: same max_length than CremeUser.first_name
    description = TextField(_(u'Description'), blank=True, null=True).set_tags(optional=True)
    skype       = CharField('Skype', max_length=100, blank=True, null=True)\
                           .set_tags(optional=True)
    phone       = PhoneField(_(u'Phone number'), max_length=100, blank=True, null=True)\
                            .set_tags(optional=True)
    mobile      = PhoneField(_(u'Mobile'), max_length=100, blank=True, null=True)\
                            .set_tags(optional=True)
    fax         = CharField(_(u'Fax'), max_length=100, blank=True, null=True)\
                           .set_tags(optional=True)
    position    = ForeignKey(Position, verbose_name=_(u'Position'),
                             blank=True, null=True, on_delete=SET_NULL,
                            ).set_tags(optional=True)
    full_position = CharField(_(u'Detailed position'), max_length=500,
                              blank=True, null=True,
                             ).set_tags(optional=True)
    sector      = ForeignKey(Sector, verbose_name=_(u'Line of business'),
                             blank=True, null=True, on_delete=SET_NULL,
                            ).set_tags(optional=True)
    email       = EmailField(_(u'Email address'), blank=True, null=True).set_tags(optional=True)
    url_site    = URLField(_(u'Web Site'), max_length=500, blank=True, null=True)\
                          .set_tags(optional=True)
    language    = ManyToManyField(Language, verbose_name=_(u'Spoken language(s)'),
                                  blank=True, editable=False,
                                 ).set_tags(viewable=False) # TODO: remove this field
    is_user  = ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_(u'Related user'),
                          blank=True, null=True, related_name='related_contact',
                          on_delete=SET_NULL, editable=False
                         ).set_tags(clonable=False) \
                          .set_null_label(pgettext_lazy('persons-is_user', u'None'))
    birthday = DateField(_(u'Birthday'), blank=True, null=True).set_tags(optional=True)
    image    = ForeignKey(Image, verbose_name=_(u'Photograph'),
                          blank=True, null=True, on_delete=SET_NULL,
                         ).set_tags(optional=True)

    # objects = CremeEntityManager()

    # Needed because we expand its function fields in other apps (ie. billing)
    # TODO: refactor
    function_fields = CremeEntity.function_fields.new()

    creation_label = _('Add a contact')

    class Meta:
        abstract = True
        app_label = "persons"
        ordering = ('last_name', 'first_name')
        verbose_name = _(u'Contact')
        verbose_name_plural = _(u'Contacts')

    def __unicode__(self):
        civ = self.civility

        if civ and civ.shortcut:
            return ugettext('%(civility)s %(first_name)s %(last_name)s') % {
                        'civility':   civ.shortcut,
                        'first_name': self.first_name,
                        'last_name':  self.last_name,
                    }

        if self.first_name:
            return ugettext('%(first_name)s %(last_name)s') % {
                            'first_name': self.first_name,
                            'last_name':  self.last_name,
                        }

        return self.last_name or ''

    def _check_deletion(self):
        if self.is_user is not None:
            raise SpecificProtectedError(ugettext(u'A user is associated with this contact.'),
                                         [self]
                                        )

    def clean(self):
        if self.is_user_id:
            if not self.first_name:
                raise ValidationError(ugettext('This Contact is related to a user and must have a first name.'))

            if not self.email:
                raise ValidationError(ugettext('This Contact is related to a user and must have an e-mail address.'))

    def get_employers(self):
        return get_organisation_model().objects.filter(relations__type=REL_OBJ_EMPLOYED_BY,
                                                       relations__object_entity=self.id,
                                                      )

    def get_absolute_url(self):
        return reverse('persons__view_contact', args=(self.id,))

    @staticmethod
    def get_create_absolute_url():
        return reverse('persons__create_contact')

    def get_edit_absolute_url(self):
        return reverse('persons__edit_contact', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
        return reverse('persons__list_contacts')

    def delete(self):
        self._check_deletion()  # Should not be useful (trashing should be blocked too)
        super(AbstractContact, self).delete()

    def _post_save_clone(self, source):
        self._aux_post_save_clone(source)

    def save(self, *args, **kwargs):
        super(AbstractContact, self).save(*args, **kwargs)

        rel_user = self.is_user
        if rel_user:
            rel_user._disable_sync_with_contact = True

            update_model_instance(rel_user,
                                  last_name=self.last_name,
                                  first_name=self.first_name or '',
                                  email=self.email or '',
                                 )

    def trash(self):
        self._check_deletion()
        super(AbstractContact, self).trash()


class Contact(AbstractContact):
    class Meta(AbstractContact.Meta):
        swappable = 'PERSONS_CONTACT_MODEL'


# Manage the related User ------------------------------------------------------

def _create_linked_contact(user):
    return get_contact_model().objects\
                              .create(user=user, is_user=user,
                                      last_name=user.last_name or user.username.title(),
                                      first_name=user.first_name or _('N/A'),
                                      email=user.email or _('replaceMe@byYourAddress.com'),
                                      # TODO assert user is not a team + enforce non team clean() ?
                                     )


def _get_linked_contact(self):
    contact = getattr(self, '_linked_contact_cache', None)

    if contact is None:
        contacts = get_contact_model().objects.filter(is_user=self)[:2]

        if not contacts:
            logger.critical('User "%s" has no related Contact => we create it', self.username)
            contact = _create_linked_contact(self)
        else:
            if len(contacts) > 1:
                # TODO: repair ? (beware to race condition)
                logger.critical('User "%s" has several related Contacts !', self.username)

            contact = contacts[0]

    self._linked_contact_cache = contact

    return contact
