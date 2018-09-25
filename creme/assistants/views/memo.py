# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth.decorators import login_required
from creme.creme_core.views import generic

from ..forms.memo import MemoForm
from ..models import Memo


# @login_required
# def add(request, entity_id):
#     return generic.add_to_entity(request, entity_id, MemoForm, _('New Memo for «%s»'),
#                                  submit_label=_('Save the memo'),
#                                 )
class MemoCreation(generic.add.AddingToEntity):
    model = Memo
    form_class = MemoForm
    title_format = _('New memo for «{}»')


@login_required
def edit(request, memo_id):
    return generic.edit_related_to_entity(request, memo_id, Memo, MemoForm, _('Memo for «%s»'))
