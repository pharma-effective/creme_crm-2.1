# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2019  Hybird
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

from collections import OrderedDict

from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, YEARLY, MONTHLY, WEEKLY, DAILY, HOURLY, MINUTELY  # SECONDLY

from django.utils.translation import gettext_lazy as _, ngettext


class DatePeriod:
    name = 'base_date_period'  # Overload
    verbose_name = 'Date period'  # Overload

    def __str__(self):
        return str(self.verbose_name)

    def __eq__(self, other_dp):
        try:
            other_td = other_dp.as_timedelta()
        except:
            return False

        return self.as_timedelta() == other_td

    def __ne__(self, other_dp):
        return not self == other_dp

    def as_timedelta(self):
        raise NotImplementedError

    def _value_as_dict(self):
        "Period as a jsonifiable dictionary"
        raise NotImplementedError

    def as_rrule(self):
        "Period as a dateutil recurrent rule"
        raise NotImplementedError

    def as_dict(self):
        "Period as a jsonifiable dictionary"
        d = {'type': self.name}
        d.update(self._value_as_dict())

        return d


class SimpleValueDatePeriod(DatePeriod):
    # frequency = ...  TO BE DEFINED

    def __init__(self, value):
        self._value = value

    def __str__(self):
        value = self._value
        # return self._ungettext(self._value).format(number=value)
        return self._ngettext(self._value).format(number=value)

    # def _ungettext(self, value):
    def _ngettext(self, value):
        raise NotImplementedError

    def as_rrule(self, **kwargs):
        return rrule(self.frequency, interval=self._value, **kwargs)

    def as_timedelta(self):
        return relativedelta(**{self.name: self._value})

    def _value_as_dict(self):
        return {'value': self._value}


class MinutesPeriod(SimpleValueDatePeriod):
    name = 'minutes'
    verbose_name = _('Minute(s)')
    frequency = MINUTELY

    # def _ungettext(self, value):
    def _ngettext(self, value):
        return ngettext('{number} minute', '{number} minutes', value)


class HoursPeriod(SimpleValueDatePeriod):
    name         = 'hours'
    verbose_name = _('Hour(s)')
    frequency = HOURLY

    # def _ungettext(self, value):
    def _ngettext(self, value):
        return ngettext('{number} hour', '{number} hours', value)


class DaysPeriod(SimpleValueDatePeriod):
    name = 'days'
    verbose_name = _('Day(s)')
    frequency = DAILY

    # def _ungettext(self, value):
    def _ngettext(self, value):
        return ngettext('{number} day', '{number} days', value)


class WeeksPeriod(SimpleValueDatePeriod):
    name = 'weeks'
    verbose_name = _('Week(s)')
    frequency = WEEKLY

    # def _ungettext(self, value):
    def _ngettext(self, value):
        return ngettext('{number} week', '{number} weeks', value)


class MonthsPeriod(SimpleValueDatePeriod):
    name = 'months'
    verbose_name = _('Month(s)')
    frequency = MONTHLY

    # def _ungettext(self, value):
    def _ngettext(self, value):
        return ngettext('{number} month', '{number} months', value)


class YearsPeriod(SimpleValueDatePeriod):
    name = 'years'
    verbose_name = _('Year(s)')
    frequency = YEARLY

    # def _ungettext(self, value):
    def _ngettext(self, value):
        return ngettext('{number} year', '{number} years', value)


class DatePeriodRegistry:
    class RegistrationError(Exception):
        pass

    def __init__(self, *periods):
        self._periods = OrderedDict()
        self.register(*periods)

    def choices(self, choices=None):
        """Return a list of tuples which can be used to build the DatePeriodField formfield.
        @param choices List of names or None, used to filter the registry elements.
                       If None provided, return all the elements.
        @return The tuples (name, period_klass.verbose_name) of registry elements.
        """
        is_allowed = (lambda name: True) if choices is None else \
                     lambda name: name in choices

        for name, period_klass in self._periods.items():
            if is_allowed(name):
                yield name, period_klass.verbose_name

    def get_period(self, name, *args):
        klass = self._periods.get(name)

        if not klass:
            return None

        return klass(*args)

    def deserialize(self, dict_value):
        return self.get_period(dict_value['type'], dict_value['value'])

    def register(self, *periods):
        periods_map = self._periods

        for period in periods:
            name = period.name

            if name in periods_map:
                raise self.RegistrationError(
                    "Duplicate date period's id or period registered twice : {}".format(name)
                )

            periods_map[name] = period


date_period_registry = DatePeriodRegistry(MinutesPeriod, HoursPeriod, DaysPeriod,
                                          WeeksPeriod, MonthsPeriod, YearsPeriod,
                                         )
