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

import warnings

from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from creme.creme_core.auth import build_creation_perm as cperm
from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.models import CremeEntity
from creme.creme_core.views import generic

from .. import get_folder_model, get_document_model
from ..constants import DEFAULT_HFILTER_DOCUMENT
from ..forms import document as doc_forms


Document = get_document_model()

# Function views --------------------------------------------------------------


def abstract_add_document(request, form=doc_forms.DocumentCreateForm,
                          submit_label=Document.save_label,
                         ):
    warnings.warn('documents.views.document.abstract_add_document() is deprecated ; '
                  'use the class-based view DocumentCreation instead.',
                  DeprecationWarning
                 )

    folder = get_folder_model().objects.first()

    return generic.add_entity(
        request, form,
        # TODO: uncomment when CreatorEntityField can be initialized with instance..
        # # extra_initial={'folder': Folder.objects.first()},
        # extra_initial={'folder': folder.id if folder else None},
        extra_initial={'linked_folder': folder.id if folder else None},
        extra_template_dict={'submit_label': submit_label},
    )


# def abstract_add_related_document(request, entity_id,
#                                   form=doc_forms.RelatedDocumentCreateForm,
#                                   title=_('New document for «%s»'),
#                                   submit_label=Document.save_label,
#                                  ):
#     entity = get_object_or_404(CremeEntity, pk=entity_id)
#     user = request.user
#
#     user.has_perm_to_view_or_die(entity)
#     user.has_perm_to_link_or_die(entity)
#     user.has_perm_to_link_or_die(Document, owner=None)
#
#     return generic.add_model_with_popup(request, form, title % entity,
#                                         initial={'entity': entity},
#                                         submit_label=submit_label,
#                                        )


def abstract_edit_document(request, document_id, form=doc_forms.DocumentEditForm):
    warnings.warn('documents.views.document.abstract_edit_document() is deprecated ; '
                  'use the class-based view DocumentEdition instead.',
                  DeprecationWarning
                 )
    return generic.edit_entity(request, document_id, Document, form)


def abstract_view_document(request, object_id,
                           template='documents/view_document.html',
                          ):
    warnings.warn('documents.views.document.abstract_view_document() is deprecated ; '
                  'use the class-based view DocumentDetail instead.',
                  DeprecationWarning
                 )
    return generic.view_entity(request, object_id, Document, template=template)


@login_required
@permission_required(('documents', cperm(Document)))
def add(request):
    warnings.warn('documents.views.document.add() is deprecated.', DeprecationWarning)
    return abstract_add_document(request)


# @login_required
# @permission_required(('documents', cperm(Document)))
# def add_related(request, entity_id):
#     return abstract_add_related_document(request, entity_id)


@login_required
@permission_required('documents')
def edit(request, document_id):
    warnings.warn('documents.views.document.edit() is deprecated.', DeprecationWarning)
    return abstract_edit_document(request, document_id)


@login_required
@permission_required('documents')
def detailview(request, object_id):
    warnings.warn('documents.views.document.detailview() is deprecated.', DeprecationWarning)
    return abstract_view_document(request, object_id)


@login_required
@permission_required('documents')
def listview(request):
    return generic.list_view(request, Document, hf_pk=DEFAULT_HFILTER_DOCUMENT)


# Class-based views  ----------------------------------------------------------

class DocumentCreation(generic.add.EntityCreation):
    model = Document
    form_class = doc_forms.DocumentCreateForm

    def get_initial(self):
        initial = super().get_initial()
        # TODO: would be cool to initialize with an instance like:
        #       initial['linked_folder'] = get_folder_model().objects.first()
        folder = get_folder_model().objects.first()
        initial['linked_folder'] = folder.id if folder else None

        return initial


class RelatedDocumentCreation(generic.add.AddingToEntity):
    model = Document
    form_class = doc_forms.RelatedDocumentCreateForm
    permissions = ['documents', cperm(Document)]
    title_format = _('New document for «{}»')

    def check_related_entity_permissions(self, entity, user):
        user.has_perm_to_view_or_die(entity)
        user.has_perm_to_link_or_die(entity)

    def check_view_permissions(self, user):
        super().check_view_permissions(user=user)
        user.has_perm_to_link_or_die(Document, owner=None)


class DocumentDetail(generic.detailview.EntityDetail):
    model = Document
    template_name = 'documents/view_document.html'
    pk_url_kwarg = 'document_id'


class DocumentEdition(generic.edit.EntityEdition):
    model = Document
    form_class = doc_forms.DocumentEditForm
    pk_url_kwarg = 'document_id'
