# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme_core.registry import creme_registry
from creme_core.gui.menu import creme_menu

from tickets.models import Ticket

creme_registry.register_app('tickets', _(u'Tickets'), '/tickets')
creme_registry.register_entity_models(Ticket)

#TODO: i18n
creme_menu.register_app('tickets', '/tickets/', 'Tickets')
reg_menu = creme_menu.register_item
reg_menu('tickets', '/tickets/',           _(u'Portal'),       'tickets')
reg_menu('tickets', '/tickets/tickets',    _(u'All tickets'),  'tickets')
reg_menu('tickets', '/tickets/ticket/add', _(u'Add a ticket'), 'tickets.add_ticket')
