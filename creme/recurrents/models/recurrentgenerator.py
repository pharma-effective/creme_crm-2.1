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

from django.core.urlresolvers import reverse
from django.db.models import (CharField, TextField, ForeignKey, DateTimeField,
        BooleanField) #PROTECT
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import CremeEntity
from creme.creme_core.models.fields import CTypeForeignKey, DatePeriodField

#from .periodicity import Periodicity


#class RecurrentGenerator(CremeEntity):
class AbstractRecurrentGenerator(CremeEntity):
    name             = CharField(_(u'Name of the generator'), max_length=100, blank=True, null=True)
    description      = TextField(_(u'Description'), blank=True, null=True)
    first_generation = DateTimeField(_(u'Date of the first recurrent generation'))
    last_generation  = DateTimeField(_(u'Date of the last recurrent generation'), null=True, editable=False)
    #periodicity      = ForeignKey(Periodicity, verbose_name=_(u'Periodicity of the generation'), on_delete=PROTECT)
    periodicity      = DatePeriodField(_(u'Periodicity of the generation'))
    ct               = CTypeForeignKey(verbose_name=_(u'Type of the recurrent resource'), editable=False)
    template         = ForeignKey(CremeEntity, verbose_name=_(u'Related model'), related_name='template_set', editable=False)
    is_working       = BooleanField(_(u'Active ?'), editable=False, default=True) #TODO: useful ?

    creation_label = _('Add a generator')

    class Meta:
        abstract = True
        app_label = 'recurrents'
        verbose_name = _(u'Recurrent generator')
        verbose_name_plural = _(u'Recurrent generators')
        ordering = ('name',)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
#        return "/recurrents/generator/%s" % self.id
        return reverse('recurrents__view_generator', args=(self.id,))

    def get_edit_absolute_url(self):
#        return "/recurrents/generator/edit/%s" % self.id
        return reverse('recurrents__edit_generator', args=(self.id,))

    @staticmethod
    def get_lv_absolute_url():
#        return "/recurrents/generators"
        return reverse('recurrents__list_generators')


class RecurrentGenerator(AbstractRecurrentGenerator):
    class Meta(AbstractRecurrentGenerator.Meta):
        swappable = 'RECURRENTS_RGENERATOR_MODEL'
