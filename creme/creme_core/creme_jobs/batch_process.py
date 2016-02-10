# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016  Hybird
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

from functools import partial
import logging

# TODO: move in function to do lazy loading (creation of see core/task_pool) ?
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.db.transaction import atomic
from django.utils.translation import ugettext_lazy as _, ungettext, ugettext

from ..core.batch_process import BatchAction
from ..models import EntityFilter, EntityCredentials, EntityJobResult
from ..utils.chunktools import iter_as_slices
from .base import JobType


logger = logging.getLogger(__name__)


class _BatchProcessType(JobType):
    id           = JobType.generate_id('creme_core', 'batch_process')
    verbose_name = _('Batch process')

    def _get_actions(self, model, job_data):
        for kwargs in job_data['actions']:
            yield BatchAction(model, **kwargs)

    def _get_efilter(self, job_data, raise_exception=True):
        efilter = None
        efilter_id = job_data.get('efilter')

        if efilter_id:
            try:
                efilter = EntityFilter.objects.get(id=efilter_id)
            except EntityFilter.DoesNotExist:
                if raise_exception:
                    raise self.Error(ugettext('The filter does not exist anymore'))

        return efilter

    def _get_model(self, job_data):
        return ContentType.objects.get_for_id(job_data['ctype']).model_class()

    def _humanize_validation_error(self, entity, ve):
        get_field = entity._meta.get_field

        try:
            # TODO: NON_FIELD_ERRORS need to be unit tested...
            humanized = [unicode(errors) if field == NON_FIELD_ERRORS else
                         u'%s => %s' % (get_field(field).verbose_name, u', '.join(errors))
                            for field, errors in ve.message_dict.iteritems()
                        ]
        except Exception as e:
            logger.debug('BatchProcess._humanize_validation_error: %s', e)
            humanized = [unicode(ve)]

        return humanized

    def _execute(self, job):
        job_data = job.data
        model = self._get_model(job_data)
        entities = model.objects.filter(is_deleted=False)

        efilter = self._get_efilter(job_data)
        if efilter is not None:
            entities = efilter.filter(entities)

        already_processed = frozenset(EntityJobResult.objects.filter(job=job)
                                                     .values_list('entity_id', flat=True)
                                     )
        if already_processed:
            logger.info('BatchProcess: resuming job %s', job.id)

        entities = EntityCredentials.filter(job.user, entities, EntityCredentials.CHANGE)
        actions = list(self._get_actions(model, job_data))
        create_result = partial(EntityJobResult.objects.create, job=job)

        for entities_slice in iter_as_slices(entities, 1024):
            for entity in entities_slice:
                if entity.id in already_processed:
                    continue

                changed = False

                for action in actions:
                    if action(entity):
                        changed = True

                if changed:
                    try:
                        entity.full_clean()
                    except ValidationError as e:
                        create_result(entity=entity, messages=self._humanize_validation_error(entity, e))
                    else:
                        with atomic():
                            entity.save()
                            create_result(entity=entity)

    @property
    def results_blocks(self):
        from ..blocks import entity_job_errors_block
        return [entity_job_errors_block]

    def get_description(self, job):
        try:
            job_data = job.data
            model = self._get_model(job_data)
            desc = [ugettext('Entity type: %s') % model._meta.verbose_name]

            efilter = self._get_efilter(job_data, raise_exception=False)
            if efilter is not None:
                desc.append(ugettext('Filter: %s') % efilter)

            desc.extend(unicode(ba) for ba in self._get_actions(model, job_data))
        except Exception:  # TODO: unit test
            logger.exception('Error in _BatchProcessType.get_description')
            desc = ['?']

        return desc

    def get_stats(self, job):
        count = EntityJobResult.objects.filter(job=job, raw_messages__isnull=True).count()

        return [ungettext('%s entity has been successfully modified.',
                          '%s entities have been successfully modified.',
                          count
                         ) % count,
               ]


batch_process_type = _BatchProcessType()