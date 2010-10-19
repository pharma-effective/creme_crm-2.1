# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from itertools import izip

from django.forms import ChoiceField, BooleanField, ModelMultipleChoiceField, MultipleChoiceField
from django.utils.translation import ugettext_lazy as _

from creme_core.models import UserRole, SetCredentials, EntityCredentials
from creme_core.registry import creme_registry
from creme_core.forms import CremeForm, CremeModelForm
from creme_core.forms.fields import ListEditionField
from creme_core.forms.widgets import UnorderedMultipleChoiceWidget
from creme_core.utils import Q_creme_entity_content_types


_ALL_APPS = [(app.name, app.verbose_name) for app in creme_registry.iter_apps()]

class UserRoleCreateForm(CremeModelForm):
    creatable_ctypes = ModelMultipleChoiceField(label=_(u'Creatable resources'),
                                                queryset=Q_creme_entity_content_types(),
                                                widget=UnorderedMultipleChoiceWidget)
    allowed_apps     = MultipleChoiceField(label=_(u'Allowed applications'),
                                           choices=_ALL_APPS,
                                           widget=UnorderedMultipleChoiceWidget)
    admin_4_apps     = MultipleChoiceField(label=_(u'Administrated applications'),
                                           choices=_ALL_APPS,
                                           widget=UnorderedMultipleChoiceWidget)

    class Meta:
        model = UserRole
        exclude = ('raw_allowed_apps', 'raw_admin_4_apps')

    def save(self, *args, **kwargs):
        instance = self.instance
        cleaned  = self.cleaned_data

        instance.allowed_apps = cleaned['allowed_apps']
        instance.admin_4_apps = cleaned['admin_4_apps']

        super(UserRoleCreateForm, self).save(*args, **kwargs)


class UserRoleEditForm(UserRoleCreateForm):
    set_credentials = ListEditionField(content=(), label=_(u'Existing set credentials'),
                                       help_text=_(u'Uncheck the credentials you want to delete.'),
                                       only_delete=True, required=False)

    def __init__(self, *args, **kwargs):
        super(UserRoleEditForm, self).__init__(*args, **kwargs)

        fields = self.fields
        instance = self.instance

        self._creds = instance.credentials.all() #get_credentials() ?? problem with cache for updating SetCredentials lines

        fields['set_credentials'].content = [unicode(creds) for creds in self._creds]
        fields['allowed_apps'].initial = instance.allowed_apps
        fields['admin_4_apps'].initial = instance.admin_4_apps

    def save(self, *args, **kwargs):
        role = super(UserRoleEditForm, self).save(*args, **kwargs)

        creds2del = [creds.pk for creds, new_creds in izip(self._creds, self.cleaned_data['set_credentials'])
                            if new_creds is None]

        if creds2del:
            SetCredentials.objects.filter(pk__in=creds2del).delete()
            #TODO: user.update_credentials() !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        return role


class AddCredentialsForm(CremeModelForm):
    can_view   = BooleanField(label=_(u'Can view'), required=False)
    can_change = BooleanField(label=_(u'Can change'), required=False)
    can_delete = BooleanField(label=_(u'Can delete'), required=False)
    set_type   = ChoiceField(label=_(u'Type of entities set'), choices=SetCredentials.ESET_MAP.items())

    class Meta:
        model = SetCredentials
        exclude = ('role', 'value') #fields ??

    def __init__(self, role, *args, **kwargs):
        super(AddCredentialsForm, self).__init__(*args, **kwargs)
        self.role = role

    def save(self, *args, **kwargs):
        instance = self.instance
        get_data = self.cleaned_data.get

        instance.role = self.role
        instance.set_value(get_data('can_view'), get_data('can_change'), get_data('can_delete'))

        #TODO: user.update_credentials() !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        return super(AddCredentialsForm, self).save(*args, **kwargs)


class DefaultCredsForm(CremeForm):
    can_view   = BooleanField(label=_(u'Can view'), required=False)
    can_change = BooleanField(label=_(u'Can change'), required=False)
    can_delete = BooleanField(label=_(u'Can delete'), required=False)

    def __init__(self, *args, **kwargs):
        super(DefaultCredsForm, self).__init__(*args, **kwargs)

        fields   = self.fields
        defcreds = EntityCredentials.get_default_creds()

        fields['can_view'].initial   = defcreds.can_view()
        fields['can_change'].initial = defcreds.can_change()
        fields['can_delete'].initial = defcreds.can_delete()

    def save(self):
        get_data = self.cleaned_data.get
        EntityCredentials.set_default_perms(view=get_data('can_view'),
                                            change=get_data('can_change'),
                                            delete=get_data('can_delete'))
