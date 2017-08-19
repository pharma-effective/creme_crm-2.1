# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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

from creme.creme_core.gui.bricks import SimpleBrick, QuerysetBrick
from creme.creme_core.models import CremeEntity

from . import get_graph_model
from .models import RootNode


class GraphBarHatBrick(SimpleBrick):
    template_name = 'graphs/bricks/graph-hat-bar.html'


class RootNodesBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('graphs', 'root_nodes')
    dependencies  = (RootNode,)
    verbose_name  = _(u'Roots nodes of a graph')
    # template_name = 'graphs/templatetags/block_root_nodes.html'
    template_name = 'graphs/bricks/root-nodes.html'
#    target_ctypes = (Graph,)
    target_ctypes = (get_graph_model(),)

    def detailview_display(self, context):
        graph = context['object']
        btc = self.get_template_context(
                    context, graph.roots.select_related('entity'),
                    # update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, graph.pk),
                    update_url=reverse('creme_core__reload_detailview_blocks', args=(self.id_, graph.id)),
        )

        CremeEntity.populate_real_entities([node.entity for node in btc['page'].object_list])

        return self._render(btc)


class OrbitalRelationTypesBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('graphs', 'orbital_rtypes')
    dependencies  = (RootNode,)
    verbose_name  = _(u'Peripheral types of relation of a graph')
    # template_name = 'graphs/templatetags/block_orbital_rtypes.html'
    template_name = 'graphs/bricks/orbital-rtypes.html'
#    target_ctypes = (Graph,)
    target_ctypes = (get_graph_model(),)

    def detailview_display(self, context):
        graph = context['object']
        return self._render(self.get_template_context(
                    context,
                    graph.orbital_relation_types.select_related('symmetric_type'),
                    # update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, graph.pk),
                    update_url=reverse('creme_core__reload_detailview_blocks', args=(self.id_, graph.id)),
        ))