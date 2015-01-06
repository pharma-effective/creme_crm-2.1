# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014  Hybird
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

import csv
import logging
import urllib2

from functools import partial
from StringIO import StringIO
from urlparse import urlparse
from zipfile import ZipFile

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.query_utils import Q
from django.template.defaultfilters import slugify

from creme.creme_core.models import BlockDetailviewLocation, BlockMypageLocation, SettingValue
from creme.creme_core.management.commands.creme_populate import BasePopulator
from creme.creme_core.utils.chunktools import iter_as_chunk

from creme.persons.models import Contact, Organisation, Address

from .blocks import persons_maps_block, persons_filter_maps_block, who_is_around_maps_block
from .constants import DEFAULT_SEPARATING_NEIGHBOURS
from .models import Town, GeoAddress
from .setting_keys import NEIGHBOURHOOD_DISTANCE


logger = logging.getLogger(__name__)

class Populator(BasePopulator):
    dependencies = ['creme_core', 'persons']

    def populate_towns(self, iterable, defaults):
        create_town = partial(Town, **defaults)
        line = 0

        for rows in iter_as_chunk(iterable, 50):
            towns = []

            try:
                for row in rows:
                    line += 1

                    try:
                        zipcodes = row[8].split('-')
                        name, latitude, longitude = row[5], row[20], row[19]
                        slug = slugify(name)

                        for zipcode in zipcodes:
                            towns.append(create_town(name=name,
                                                     slug=slug,
                                                     zipcode=zipcode,
                                                     latitude=latitude,
                                                     longitude=longitude,))
                    except Exception as e:
                        logger.error('invalid town data (line %d) : %s', line, e)

                existings = frozenset(Town.objects.filter(zipcode__in=(t.zipcode for t in towns),
                                                          slug__in=(t.slug for t in towns))
                                                  .values_list('zipcode', flat=True)
                                     )
                Town.objects.bulk_create([t for t in towns if t.zipcode not in existings])
            except Exception as e:
                logger.error(e)

    def _open_towns_data(self, url):
        try:
            url_info = urlparse(url)

            if url_info.scheme in ('file', ''):
                input = open(url_info.path, 'rb')
            elif url_info.scheme in ('http', 'https'):
                logger.info('Downloading Towns database...')
                input = urllib2.urlopen(url)
            else:
                raise Exception('unsupported protocol %s.' % url_info.scheme)

            if url_info.path.endswith('.zip'):
                archive = ZipFile(StringIO(input.read()))
                input = archive.open(archive.namelist()[0])

            return input
        except Exception as e:
            raise Exception('Unable to open Towns database from %s : %s' % (url, e))

    def import_towns(self, url, defaults):
        try:
            input = self._open_towns_data(url)

            logger.info('Importing Towns database...')
            self.populate_towns(csv.reader(input), defaults)
        except Exception as e:
            logger.warn(e)

    def populate_addresses(self):
        GeoAddress.populate_geoaddresses(Address.objects.filter(Q(zipcode__isnull=False) | Q(city__isnull=False)))

    def populate(self):
        already_populated = SettingValue.objects.filter(key_id=NEIGHBOURHOOD_DISTANCE.id).exists()

        SettingValue.create_if_needed(key=NEIGHBOURHOOD_DISTANCE, user=None, value=DEFAULT_SEPARATING_NEIGHBOURS)

        if not already_populated or not Town.objects.exists():
            for url, defaults in settings.GEOLOCATION_TOWNS:
                self.import_towns(url, defaults)

        logger.info('Populating geolocations of existing addresses...')
        self.populate_addresses()

        if not already_populated:
            BlockDetailviewLocation.create(block_id=persons_maps_block.id_, order=70, zone=BlockDetailviewLocation.LEFT, model=Organisation)
            BlockDetailviewLocation.create(block_id=persons_maps_block.id_, order=70, zone=BlockDetailviewLocation.LEFT, model=Contact)
            BlockDetailviewLocation.create(block_id=who_is_around_maps_block.id_, order=600, zone=BlockDetailviewLocation.BOTTOM, model=Organisation)
            BlockDetailviewLocation.create(block_id=who_is_around_maps_block.id_, order=600, zone=BlockDetailviewLocation.BOTTOM, model=Contact)

            BlockMypageLocation.create(block_id=persons_filter_maps_block.id_, order=20)

            try:
                # add this bloc only if the root user exists (creme_core populated)
                root = User.objects.get(pk=1)

                logger.info('Creme core is installed => the block PersonsFilterMap can be activated')
                BlockMypageLocation.create(block_id=persons_filter_maps_block.id_, order=8, user=root)
            except User.DoesNotExist:
                pass
