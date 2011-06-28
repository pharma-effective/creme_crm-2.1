# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext as _

from creme_core.models import RelationType, BlockConfigItem, ButtonMenuItem, SearchConfigItem, HeaderFilterItem, HeaderFilter
from creme_core.utils import create_or_update as create
from creme_core.management.commands.creme_populate import BasePopulator
from creme_core.utils.id_generator import generate_string_id_and_save

from creme_config.constants import USER_SETTINGS_BLOCK_PREFIX

from persons.models import Contact

from activities.models import *
from activities.blocks import future_activities_block, past_activities_block, user_calendars_block
from activities.buttons import add_meeting_button, add_phonecall_button, add_task_button
from activities.constants import *


class Populator(BasePopulator):
    dependencies = ['creme.creme_core']

    def populate(self, *args, **kwargs):
        RelationType.create((REL_SUB_LINKED_2_ACTIVITY, _(u"related to the activity")),
                            (REL_OBJ_LINKED_2_ACTIVITY, _(u"(activity) related to"),        [Activity, Meeting, PhoneCall, Task])
                           )
        RelationType.create((REL_SUB_ACTIVITY_SUBJECT, _(u"is subject of the activity")),
                            (REL_OBJ_ACTIVITY_SUBJECT, _(u'(activity) is to subject'),      [Activity, Meeting, PhoneCall, Task])
                           )
        RelationType.create((REL_SUB_PART_2_ACTIVITY,  _(u"participates to the activity"),  [Contact]),
                            (REL_OBJ_PART_2_ACTIVITY,  _(u'(activity) has as participant'), [Activity, Meeting, PhoneCall, Task])
                           )

        create(PhoneCallType, PHONECALLTYPE_INCOMING, name=_(u"Incoming"), description=_(u"Incoming call"))
        create(PhoneCallType, PHONECALLTYPE_OUTGOING, name=_(u"Outgoing"), description=_(u"Outgoing call"))
        create(PhoneCallType, PHONECALLTYPE_OTHER,    name=_(u"Other"),    description=_(u"Example: a conference"))

        create(Status, STATUS_PLANNED,     name=_(u"Planned"),     description=_(u"Planned"))
        create(Status, STATUS_IN_PROGRESS, name=_(u"In progress"), description=_(u"In progress"))
        create(Status, STATUS_DONE,        name=_(u"Done"),        description=_(u"Done"))
        create(Status, STATUS_DELAYED,     name=_(u"Delayed"),     description=_(u"Delayed"))
        create(Status, STATUS_CANCELLED,   name=_(u"Cancelled"),   description=_(u"Cancelled"))

        create(ActivityType, ACTIVITYTYPE_TASK,      name=_(u"Task"),            color="987654", default_day_duration=0, default_hour_duration="00:15:00", is_custom=False)
        create(ActivityType, ACTIVITYTYPE_MEETING,   name=_(u"Meeting"),         color="456FFF", default_day_duration=0, default_hour_duration="00:15:00", is_custom=False)
        create(ActivityType, ACTIVITYTYPE_PHONECALL, name=_(u"Phone call"),      color="A24BBB", default_day_duration=0, default_hour_duration="00:15:00", is_custom=False)
        create(ActivityType, ACTIVITYTYPE_GATHERING, name=_(u"Gathering"),       color="F23C39", default_day_duration=0, default_hour_duration="00:15:00", is_custom=False)
        create(ActivityType, ACTIVITYTYPE_SHOW,      name=_(u"Show"),            color="8DE501", default_day_duration=1, default_hour_duration="00:00:00", is_custom=False)
        create(ActivityType, ACTIVITYTYPE_DEMO,      name=_(u"Demonstration"),   color="4EEF65", default_day_duration=0, default_hour_duration="01:00:00", is_custom=False)
        create(ActivityType, ACTIVITYTYPE_INDISPO,   name=_(u"Indisponibility"), color="CC0000", default_day_duration=1, default_hour_duration="00:00:00", is_custom=False)

        hf   = HeaderFilter.create(pk='activities-hf', name=_(u'Activity view'), model=Activity)
        hf.set_items([HeaderFilterItem.build_4_field(model=Activity, name='title'),
                      HeaderFilterItem.build_4_field(model=Activity, name='start'),
                      HeaderFilterItem.build_4_field(model=Activity, name='end'),
                      HeaderFilterItem.build_4_field(model=Activity, name='type__name'),
                      HeaderFilterItem.build_4_field(model=Activity, name='status__name'),
                     ])

        BlockConfigItem.create(pk='activities-future_activities_block', block_id=future_activities_block.id_, order=20, on_portal=False)
        BlockConfigItem.create(pk='activities-past_activities_block',   block_id=past_activities_block.id_,   order=21, on_portal=False)

        ButtonMenuItem.create('activities-add_meeting_button',   model=None, button=add_meeting_button,   order=10)
        ButtonMenuItem.create('activities-add_phonecall_button', model=None, button=add_phonecall_button, order=11)
        ButtonMenuItem.create('activities-add_task_button',      model=None, button=add_task_button,      order=12)

        SearchConfigItem.create(Activity, ['title', 'description', 'type__name'])

        for user in User.objects.all():
            Calendar.get_user_default_calendar(user)

        if not BlockConfigItem.objects.filter(block_id__in=[user_calendars_block.id_]).exists():
            generate_string_id_and_save(BlockConfigItem,
                                        [BlockConfigItem(content_type=ContentType.objects.get_for_model(User), block_id=user_calendars_block.id_, order=1, on_portal=False)],
                                        USER_SETTINGS_BLOCK_PREFIX)
