# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from collections import defaultdict
from copy import copy
from datetime import datetime, timedelta
from functools import partial
# from json import dumps as jsondumps
import logging

from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Prefetch
from django.db.transaction import atomic
from django.http import HttpResponse  # Http404
from django.shortcuts import render  # get_object_or_404
from django.urls import reverse
# from django.utils.html import escape
from django.utils.timezone import now, make_naive, get_current_timezone
from django.utils.translation import gettext_lazy as _, gettext

# from creme.creme_core.auth import build_creation_perm as cperm
# from creme.creme_core.auth.decorators import login_required, permission_required
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.http import CremeJsonResponse
from creme.creme_core.models import EntityCredentials, Job, DeletionCommand
from creme.creme_core.utils import get_from_POST_or_404, bool_from_str_extended
from creme.creme_core.utils.dates import make_aware_dt
from creme.creme_core.utils.unicode_collation import collator
from creme.creme_core.views import generic  # decorators
# from creme.creme_core.views.decorators import jsonify

# from creme.persons import get_contact_model

from .. import get_activity_model, constants
from ..forms import calendar as calendar_forms
from ..models import Calendar
from ..utils import get_last_day_of_a_month, check_activity_collisions

logger = logging.getLogger(__name__)
Activity = get_activity_model()


# def _activity_2_dict(activity, user):
#     "Returns a 'jsonifiable' dictionary"
#     tz = get_current_timezone()
#     start = make_naive(activity.start, tz)
#     end   = make_naive(activity.end, tz)
#
#     is_all_day = activity.is_all_day or activity.floating_type == constants.FLOATING_TIME
#
#     if start == end and not is_all_day:
#         end += timedelta(seconds=1)
#
#     calendar = activity.calendar  # NB: _get_one_activity_per_calendar() adds this 'attribute'
#
#     return {
#         'id':           activity.id,
#         'title':        activity.get_title_for_calendar(),
#         'start':        start.isoformat(),
#         'end':          end.isoformat(),
#         'url':          reverse('activities__view_activity_popup', args=(activity.id,)),
#         'calendar_color': '#{}'.format(calendar.get_color),
#         'allDay':       is_all_day,
#         'editable':     user.has_perm_to_change(activity),
#         'calendar':     calendar.id,
#         'type':         activity.type.name,
#     }


# def _get_datetime(data, key, default_func):
#     timestamp = data.get(key)
#     if timestamp is not None:
#         try:
#             return make_aware_dt(datetime.fromtimestamp(float(timestamp)))
#         except Exception:
#             logger.exception('_get_datetime(key=%s)', key)
#
#     return default_func()


# def _get_one_activity_per_calendar(calendar_ids, activities):
#     for activity in activities:
#         for calendar in activity.calendars.filter(id__in=calendar_ids):
#             copied = copy(activity)
#             copied.calendar = calendar
#             yield copied


def _js_timestamp_to_datetime(timestamp):
    "@raise ValueError"
    return make_aware_dt(datetime.fromtimestamp(float(timestamp) / 1000))  # JS gives us milliseconds


# def _filter_authorized_calendars(user, calendar_ids):
#     return list(Calendar.objects.filter((Q(is_public=True) | Q(user=user)) &
#                                          Q(id__in=[cal_id
#                                                      for cal_id in calendar_ids
#                                                        if cal_id.isdigit()
#                                                   ]
#                                           )
#                                         )
#                                 .values_list('id', flat=True)
#                )


# @login_required
# @permission_required('activities')
# def user_calendar(request):
#     user = request.user
#     getlist = request.POST.getlist  # todo: post ??
#
#     # We don't really need the default calendar but this line creates one when the user has no calendar.
#     Calendar.get_user_default_calendar(user)
#
#     selected_calendars = getlist('selected_calendars')
#     if selected_calendars:
#         selected_calendars = _filter_authorized_calendars(user, selected_calendars)
#
#     calendar_ids = selected_calendars or [c.id for c in Calendar.get_user_calendars(user)]
#
#     others_calendars = defaultdict(list)
#     creme_calendars_by_user = defaultdict(list)
#
#     calendars = Calendar.objects.exclude(user=user).filter(is_public=True)
#
#     for calendar in calendars:
#         cal_user = calendar.user
#         filter_key = escape('{} {} {}'.format(
#                                 cal_user.username,
#                                 cal_user.first_name,
#                                 cal_user.last_name,
#                            ))
#         cal_user.filter_key = filter_key
#         others_calendars[cal_user].append(calendar)
#         creme_calendars_by_user[filter_key].append({'name': escape(calendar.name),
#                                                     'id': calendar.id,
#                                                    })
#
#     floating_activities = []
#     for activity in Activity.objects.filter(floating_type=constants.FLOATING,
#                                             relations__type=constants.REL_OBJ_PART_2_ACTIVITY,
#                                             relations__object_entity=user.linked_contact.id,
#                                             is_deleted=False,
#                                            ):
#         try:
#             activity.calendar = activity.calendars.get(user=user)
#         except Calendar.DoesNotExist:
#             pass
#         else:
#             floating_activities.append(activity)
#
#     return render(request, 'activities/calendar.html',
#                   {'user_username':           user.username,
#                    'events_url':              reverse('activities__calendars_activities'),
#                    'max_element_search':      constants.MAX_ELEMENT_SEARCH,
#                    'my_calendars':            Calendar.objects.filter(user=user),
#                    'others_calendars':        dict(others_calendars),
#                    'n_others_calendars':      len(calendars),
#                    'creme_calendars_by_user': jsondumps(creme_calendars_by_user),  # todo: use '|jsonify' ?
#                    'current_calendars':       [str(id) for id in calendar_ids],
#                    'creation_perm':           user.has_perm(cperm(Activity)),
#                    # todo only floating activities assigned to logged user ??
#                    'floating_activities':     floating_activities,
#                   }
#                  )
class CalendarView(generic.CheckedTemplateView):
    template_name = 'activities/calendar.html'
    permissions = 'activities'

    calendar_id_arg = 'calendar_id'
    calendars_search_threshold = 10
    floating_activities_search_threshold = 10

    calendar_ids_session_key = 'activities__calendars'

    @staticmethod
    def _filter_default_calendars(user, calendars):
        user_id = user.id
        for calendar in calendars:
            if calendar.user_id == user_id and calendar.is_default:
                yield calendar

    def get_floating_activities(self):
        # TODO only floating activities assigned to logged user ??
        floating_activities = []
        user = self.request.user

        for activity in Activity.objects.filter(
                floating_type=constants.FLOATING,
                relations__type=constants.REL_OBJ_PART_2_ACTIVITY,
                relations__object_entity=user.linked_contact.id,
                is_deleted=False,
               ):
            try:
                activity.calendar = activity.calendars.get(user=user)
            except Calendar.DoesNotExist:
                pass
            else:
                floating_activities.append(activity)

        return floating_activities

    def get_selected_calendar_ids(self, calendars):
        request = self.request
        request_calendar_ids = request.GET.getlist(self.calendar_id_arg)

        if request_calendar_ids:
            # TODO: error (message VS exception) if not int ?
            raw_ids = {int(cal_id) for cal_id in request_calendar_ids if cal_id.isdigit()}
        else:
            raw_ids = {*request.session.get(self.calendar_ids_session_key, ())}

        return [
            calendar.id for calendar in calendars if calendar.id in raw_ids
        ]

    def get_calendars(self, user):
        # NB: we retrieve all the user's Calendars to check the presence of the
        #     default one (& create it if needed) by avoiding an extra query.
        calendars = [*Calendar.objects.filter(
            Q(user=user) |
            Q(is_public=True, user__is_staff=False, user__is_active=True)
        )]

        if next(self._filter_default_calendars(user, calendars), None) is None:
            calendars.append(Calendar.objects.create_default_calendar(
                user=user,
                is_public=bool(settings.ACTIVITIES_DEFAULT_CALENDAR_IS_PUBLIC),
            ))

        return calendars

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        calendars = self.get_calendars(user)
        # TODO: populate 'user' ?

        my_calendars = []
        others_calendars = defaultdict(list)
        others_calendar_ids = []

        for calendar in calendars:
            cal_user = calendar.user

            if cal_user == user:
                my_calendars.append(calendar)
            else:
                others_calendars[cal_user].append(calendar)
                others_calendar_ids.append(calendar.id)

        context['my_calendars'] = my_calendars

        sort_key = collator.sort_key
        other_users = [*others_calendars.keys()]
        other_users.sort(key=lambda u: sort_key(str(u)))
        context['others_calendars'] = [(u, others_calendars[u]) for u in other_users]

        selected_calendars_ids = set(
            self.get_selected_calendar_ids(calendars) or
            (calendar.id
                for calendar in self._filter_default_calendars(user, calendars)
            )
        )
        context['my_selected_calendar_ids'] = {
            cal.id for cal in my_calendars if cal.id in selected_calendars_ids
        }
        context['others_selected_calendar_ids'] = {
            cal_id for cal_id in others_calendar_ids if cal_id in selected_calendars_ids
        }

        context['enable_calendars_search'] = (
            len(calendars) >= self.calendars_search_threshold
        )  # TODO: unit test for <True> case

        context['floating_activities'] = f_activities = self.get_floating_activities()
        context['enable_floating_activities_search'] = (
            len(f_activities) >= self.floating_activities_search_threshold
        )  # TODO: unit test for <True> case

        return context


# @login_required
# @permission_required('activities')
# @jsonify
# def get_users_activities(request):
#     GET = request.GET
#     calendar_ids = GET.getlist('calendar_id')
#
#     user = request.user
#     contacts = list(get_contact_model().objects.exclude(is_user=None)
#                                        .values_list('id', flat=True)
#                    )  # NB: list() to avoid inner query
#     users_cal_ids = _filter_authorized_calendars(user, calendar_ids)
#
#     start = _get_datetime(GET, 'start', (lambda: now().replace(day=1)))
#     end   = _get_datetime(GET, 'end',   (lambda: get_last_day_of_a_month(start)))
#
#     activities = EntityCredentials.filter(
#         user,
#         Activity.objects.filter(is_deleted=False)
#                         .filter(Q(start__range=(start, end)) |
#                                 Q(end__gt=start, start__lt=end)
#                                )
#                         .filter(Q(calendars__pk__in=users_cal_ids) |
#                                 Q(type=constants.ACTIVITYTYPE_INDISPO,
#                                   relations__type=constants.REL_OBJ_PART_2_ACTIVITY,
#                                   relations__object_entity__in=contacts,
#                                  )
#                                ).distinct()
#     )
#
#     return [
#         _activity_2_dict(activity, user)
#             for activity in _get_one_activity_per_calendar(calendar_ids, activities)
#     ]
class CalendarsMixin:
    calendar_id_arg = 'calendar_id'

    @staticmethod
    def _str_ids_2_int_ids(str_ids):
        for str_id in str_ids:
            if str_id.isdigit():
                yield int(str_id)

    def get_calendar_raw_ids(self, request):
        return request.GET.getlist(self.calendar_id_arg)

    def get_calendars(self, request):
        calendar_ids = [*self._str_ids_2_int_ids(self.get_calendar_raw_ids(request))]

        return Calendar.objects.filter(
            (Q(is_public=True) | Q(user=request.user)) & Q(id__in=calendar_ids)
        ) if calendar_ids else Calendar.objects.none()


class ActivitiesData(CalendarsMixin, generic.CheckedView):
    response_class = CremeJsonResponse
    start_arg = 'start'
    end_arg = 'end'

    calendar_ids_session_key = CalendarView.calendar_ids_session_key

    def get(self, request, *args, **kwargs):
        return self.response_class(
            self.get_activities_data(request),
            safe=False,  # Result is not a dictionary
        )

    @staticmethod
    def _activity_2_dict(activity, user):
        "Returns a 'jsonifiable' dictionary."
        tz = get_current_timezone()
        start = make_naive(activity.start, tz)
        end = make_naive(activity.end, tz)

        # HACK: to hide start time of floating time activities,
        #       only way to do that without change JS calendar API.
        is_all_day = activity.is_all_day or activity.floating_type == constants.FLOATING_TIME

        if start == end and not is_all_day:
            end += timedelta(seconds=1)

        # NB: _get_one_activity_per_calendar() adds this 'attribute'
        calendar = activity.calendar

        return {
            'id':    activity.id,
            # 'title': activity.get_title_for_calendar(),
            'title': activity.title,

            'start':  start.isoformat(),
            'end':    end.isoformat(),
            'allDay': is_all_day,

            'url': reverse('activities__view_activity_popup', args=(activity.id,)),

            # 'calendar_color': '#{}'.format(calendar.get_color),
            'color':    '#{}'.format(calendar.get_color),
            'editable': user.has_perm_to_change(activity),
            'calendar': calendar.id,
            'type':     activity.type.name,
        }

    @staticmethod
    def _get_datetime(*, request, key):
        timestamp = request.GET.get(key)

        if timestamp is not None:
            try:
                return make_aware_dt(datetime.fromtimestamp(float(timestamp)))
            except Exception:
                logger.exception('ActivitiesData._get_datetime(key=%s)', key)

    @staticmethod
    def _get_one_activity_per_calendar(activities):
        for activity in activities:
            # "concerned_calendars" is added by get_activities_data()
            for calendar in activity.concerned_calendars:
                copied = copy(activity)
                copied.calendar = calendar
                yield copied

    def get_activities_data(self, request):
        user = request.user

        calendar_ids = [cal.id for cal in self.get_calendars(request)]
        self.save_calendar_ids(request, calendar_ids)

        # contacts = [*get_contact_model().objects
        #                                 .exclude(is_user=None)
        #                                 .values_list('id', flat=True)
        #            ]  # NB: list to avoid inner query

        start = self.get_start(request)
        end   = self.get_end(request=request, start=start)

        # TODO: label when no calendar related to the participant of an unavailability
        activities = EntityCredentials.filter(
            user,
            Activity.objects
                    .filter(is_deleted=False)
                    .filter(self.get_date_q(start=start, end=end))
                    .filter(calendars__in=calendar_ids
                            # Q(calendars__in=calendar_ids)
                            # | Q(type=constants.ACTIVITYTYPE_INDISPO,
                            #     relations__type=constants.REL_OBJ_PART_2_ACTIVITY,
                            #     relations__object_entity__in=contacts,
                            #    )
                           )
                    .distinct()
                    # NB: we already filter by calendars ; maybe a future Django version
                    #     will allow us to annotate the calendar ID directly
                    #     (distinct() would have to be removed of course)
                    .prefetch_related(
                        Prefetch('calendars',
                                 queryset=Calendar.objects.filter(id__in=calendar_ids),
                                 to_attr='concerned_calendars',
                                )
                     )
        )

        activity_2_dict = partial(self._activity_2_dict, user=user)

        return [
            activity_2_dict(activity=a)
                for a in self._get_one_activity_per_calendar(activities)
        ]

    @staticmethod
    def get_date_q(start, end):
        return Q(start__range=(start, end)) | Q(end__gt=start, start__lt=end)

    def get_end(self, request, start):
        return self._get_datetime(request=request, key=self.end_arg) or \
               get_last_day_of_a_month(start)

    def get_start(self, request):
        return self._get_datetime(request=request, key=self.start_arg) or \
               now().replace(day=1)

    def save_calendar_ids(self, request, calendar_ids):
        # TODO: GET argument to avoid saving ?
        key = self.calendar_ids_session_key
        session = request.session

        if calendar_ids != session.get(key):
            session[key] = calendar_ids


class CalendarsSelection(CalendarsMixin, generic.CheckedView):
    """View which can add & remove selected calendar IDs in the session.
    It's mostly useful to remove IDs without retrieving Activities data
    (see ActivitiesData) ; the <add> command is here to get a more
    consistent/powerful API.
    """
    add_arg = 'add'
    remove_arg = 'remove'
    calendar_ids_session_key = CalendarView.calendar_ids_session_key

    def get_calendar_raw_ids(self, request):
        return request.POST.getlist(self.add_arg)

    def post(self, request, *args, **kwargs):
        session = request.session
        key = self.calendar_ids_session_key

        calendar_ids = set(session.get(key) or ())
        calendar_ids.update(cal.id for cal in self.get_calendars(request))
        ids_2remove = {*self._str_ids_2_int_ids(request.POST.getlist(self.remove_arg))}

        session[key] = [
            cal_id for cal_id in calendar_ids
                if cal_id not in ids_2remove
        ]

        return HttpResponse()


# @login_required
# @permission_required('activities')
# @jsonify
# @decorators.POST_only
# @atomic
# def update_activity_date(request):
#     POST = request.POST
#
#     act_id          = POST['id']
#     start_timestamp = POST['start']
#     end_timestamp   = POST['end']
#     is_all_day      = POST.get('allDay')
#
#     is_all_day = is_all_day.lower() in {'1', 'true'} if is_all_day else False
#
#     try:
#         activity = Activity.objects.select_for_update().get(pk=act_id)
#     except Activity.DoesNotExist as e:
#         raise Http404(str(e)) from e
#
#     request.user.has_perm_to_change_or_die(activity)
#
#     # This view is used when drag and dropping event comming from calendar
#     # or external events (floating events).
#     # Dropping a floating event on the calendar fixes it.
#     if activity.floating_type == constants.FLOATING:
#         activity.floating_type = constants.NARROW
#
#     activity.start = _js_timestamp_to_datetime(start_timestamp)
#     activity.end   = _js_timestamp_to_datetime(end_timestamp)
#
#     if is_all_day is not None and activity.floating_type != constants.FLOATING_TIME:
#         activity.is_all_day = is_all_day
#         activity.handle_all_day()
#
#     collisions = check_activity_collisions(
#         activity.start, activity.end,
#         participants=[r.object_entity for r in activity.get_participant_relations()],
#         busy=activity.busy,
#         exclude_activity_id=activity.id,
#     )
#
#     if collisions:
#         raise ConflictError(', '.join(collisions))
#
#     activity.save()
class ActivityDatesSetting(generic.base.EntityRelatedMixin, generic.CheckedView):
    """This view is used when drag & dropping Activities in the Calendar."""
    permissions = 'activities'
    entity_classes = Activity
    entity_select_for_update = True

    activity_id_arg = 'id'
    start_arg = 'start'
    end_arg = 'end'
    all_day_arg = 'allDay'

    def get_related_entity_id(self):
        return get_from_POST_or_404(self.request.POST, key=self.activity_id_arg, cast=int)

    @atomic
    def post(self, request, *args, **kwargs):
        POST = request.POST
        start = get_from_POST_or_404(POST, key=self.start_arg,
                                     cast=_js_timestamp_to_datetime
                                    )
        end = get_from_POST_or_404(POST, key=self.end_arg,
                                    cast=_js_timestamp_to_datetime
                                   )
        is_all_day = get_from_POST_or_404(POST, key=self.all_day_arg,
                                          cast=bool_from_str_extended,
                                          default='false',
                                         )

        activity = self.get_related_entity()

        # Dropping a floating Activity on the Calendar fixes it.
        if activity.floating_type == constants.FLOATING:
            activity.floating_type = constants.NARROW

        activity.start = start
        activity.end = end
        activity.is_all_day = is_all_day

        activity.handle_all_day()

        collisions = check_activity_collisions(
            activity.start, activity.end,
            participants=[r.object_entity for r in activity.get_participant_relations()],
            busy=activity.busy,
            exclude_activity_id=activity.id,
        )

        if collisions:
            raise ConflictError(', '.join(collisions))  # TODO: improve message?

        activity.save()

        return HttpResponse()


class CalendarCreation(generic.CremeModelCreationPopup):
    model = Calendar
    form_class = calendar_forms.CalendarForm
    permissions = 'activities'


class CalendarEdition(generic.CremeModelEditionPopup):
    model = Calendar
    form_class = calendar_forms.CalendarForm
    permissions = 'activities'
    pk_url_kwarg = 'calendar_id'

    def check_instance_permissions(self, instance, user):
        if instance.user != user:  # TODO: and superuser ??
            raise PermissionDenied('You cannot edit this Calendar (it is not yours).')


# @login_required
# @permission_required('activities')
# @jsonify
# @decorators.POST_only
# def delete_user_calendar(request):
#     calendar = get_object_or_404(Calendar, pk=get_from_POST_or_404(request.POST, 'id'))
#     user = request.user
#
#     # todo: factorise calendar credentials functions ?
#     if not calendar.is_custom or (not user.is_superuser and calendar.user_id != user.id):
#         raise PermissionDenied(gettext('You are not allowed to delete this calendar.'))
#
#     # Attach all existing activities to the default calendar
#     # replacement_calendar = Calendar.get_user_default_calendar(user)
#     replacement_calendar = Calendar.objects.get_default_calendar(user)
#     if replacement_calendar == calendar:
#         replacement_calendar = Calendar.objects.filter(user=user)\
#                                                .exclude(id=calendar.id)\
#                                                .order_by('id')\
#                                                .first()
#
#         if replacement_calendar is None:
#             raise ConflictError(gettext('You cannot delete your last calendar.'))
#
#     for activity in calendar.activity_set.all():
#         activity.calendars.add(replacement_calendar)
#
#     calendar.delete()
class CalendarDeletion(generic.CremeModelEditionPopup):
    model = Calendar
    form_class = calendar_forms.CalendarDeletionForm
    permissions = 'activities'
    pk_url_kwarg = 'calendar_id'
    title = _('Replace & delete «{object}»')
    job_template_name = 'creme_config/deletion-job-popup.html'

    def check_instance_permissions(self, instance, user):
        if not instance.is_custom:
            raise ConflictError(
                gettext('You cannot delete this calendar: it is not custom.')
            )

        if instance.user_id != user.id:
            raise PermissionDenied(gettext('You are not allowed to delete this calendar.'))

        if not Calendar.objects.filter(user=user).exclude(id=instance.id).exists():
            raise ConflictError(gettext('You cannot delete your last calendar.'))

        ctype = ContentType.objects.get_for_model(Calendar)
        dcom = DeletionCommand.objects.filter(content_type=ctype).first()

        if dcom is not None:
            if dcom.job.status == Job.STATUS_OK:
                dcom.job.delete()
            else:
                # TODO: if STATUS_ERROR, show a popup with the errors ?
                raise ConflictError(
                    gettext('A deletion process for an instance of «{model}» already exists.').format(
                        model=ctype,
                ))

    def form_valid(self, form):
        self.object = form.save()

        return render(request=self.request,
                      template_name=self.job_template_name,
                      context={'job': self.object.job},
                     )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = None
        kwargs['instance_to_delete'] = self.object

        return kwargs


class CalendarLinking(generic.CremeModelEditionPopup):
    model = Activity
    form_class = calendar_forms.ActivityCalendarLinkerForm
    permissions = 'activities'
    pk_url_kwarg = 'activity_id'
    title = _('Change calendar of «{object}»')
