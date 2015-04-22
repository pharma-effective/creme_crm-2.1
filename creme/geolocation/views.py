# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2015  Hybird
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

from itertools import chain
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from creme.creme_core.auth.decorators import permission_required, login_required
from creme.creme_core.models import EntityFilter
from creme.creme_core.utils import jsonify, get_from_POST_or_404
from creme.creme_core.views.decorators import POST_only

from creme.persons import get_contact_model, get_organisation_model, get_address_model
#from creme.persons.models import Address, Contact, Organisation

from .constants import DEFAULT_SEPARATING_NEIGHBOURS
from .setting_keys import NEIGHBOURHOOD_DISTANCE

from .models import GeoAddress
from .utils import address_as_dict, addresses_from_persons, get_setting


@login_required
@permission_required('persons')
@POST_only
def set_address_info(request, address_id):
    get = partial(get_from_POST_or_404, request.POST)
#    address = get_object_or_404(Address, pk=address_id)
    address = get_object_or_404(get_address_model(), pk=address_id)

    request.user.has_perm_to_change_or_die(address.owner)

    data = {'latitude':  get('latitude'),
            'longitude': get('longitude'),
            'geocoded':  get('geocoded').lower() == 'true',
            'status':    get('status')
           }

    try:
        address.geoaddress.update(**data)
    except GeoAddress.DoesNotExist:
        GeoAddress.objects.create(address=address, **data)

    return HttpResponse()

@login_required
@permission_required('persons')
@jsonify
def get_addresses_from_filter(request, filter_id):
    user = request.user
    entity_filter = get_object_or_404(EntityFilter, pk=filter_id) if filter_id else None
#    owner_groups = (Contact.objects, Organisation.objects,)
    owner_groups = (get_contact_model().objects, get_organisation_model().objects,)

    if entity_filter:
        model = entity_filter.entity_type.model_class()
        owner_groups = (entity_filter.filter(model.objects, user),)

    addresses = list(chain(*(iter(addresses_from_persons(owners, user)) for owners in owner_groups)))

    GeoAddress.populate_geoaddresses(addresses)

    return {'addresses': [address_as_dict(address) for address in addresses]}

@login_required
@permission_required('persons')
@jsonify
def get_neighbours(request, address_id, filter_id):
    user = request.user
#    source = get_object_or_404(Address, pk=address_id)
    source = get_object_or_404(get_address_model(), pk=address_id)
    distance = get_setting(NEIGHBOURHOOD_DISTANCE, DEFAULT_SEPARATING_NEIGHBOURS)
    entity_filter = get_object_or_404(EntityFilter, pk=filter_id) if filter_id else None

    query_distance = request.GET.get('distance', '')

    if query_distance.isdigit():
        distance = float(query_distance)

    neighbours = source.geoaddress.neighbours(distance).select_related('address')

    if entity_filter:
        model = entity_filter.entity_type.model_class()

        # filter owners of neighbours
        owner_ids = neighbours.values_list('address__object_id', flat=True)
        owner_ids = entity_filter.filter(model.objects.filter(is_deleted=False, pk__in=owner_ids))\
                                 .values_list('pk', flat=True)

        neighbours = neighbours.filter(address__content_type_id=ContentType.objects.get_for_model(model).pk,
                                       address__object_id__in=owner_ids)

    # filter credentials
    has_perm = user.has_perm_to_view
    addresses = [address_as_dict(neighbor.address) for neighbor in neighbours if has_perm(neighbor.address.owner)]

    return {'source_address': address_as_dict(source),
            'addresses': addresses}
