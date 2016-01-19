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
from django.utils.translation import ugettext_lazy as _

from .line import Line


class AbstractServiceLine(Line):
    creation_label = _('Add a service line')

    class Meta(Line.Meta):
        abstract = True
        verbose_name = _(u'Service line')
        verbose_name_plural = _(u'Service lines')

    def __unicode__(self):
        if self.on_the_fly_item:
            return u"On the fly service '%s'" % self.on_the_fly_item

        return u"Related to service '%s'" % self.related_item

    @staticmethod
    def get_lv_absolute_url():
        return reverse('billing__list_service_lines')


class ServiceLine(AbstractServiceLine):
    class Meta(AbstractServiceLine.Meta):
        swappable = 'BILLING_SERVICE_LINE_MODEL'
