# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2019  Hybird
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
import logging

logger = logging.getLogger(__name__)


class _EntityFilterRegistry:
    """Registry about EntityFilter components:
     - Conditions handlers.
     - Operators.
     - Operands.
    """
    class RegistrationError(Exception):
        pass

    def __init__(self, verbose_name):
        self.verbose_name = verbose_name
        self._handler_classes = OrderedDict()  # We keep the registration order for the form.
        self._operator_classes = {}
        self._operand_classes = {}

    def register_condition_handlers(self, *classes):
        """Register classes of handlers.

        @param classes: Classes inheriting
               <creme_core.core.entity_filter.condition_handler.FilterConditionHandler>.
        @return: self (to chain registrations).
        @raises: _EntityFilterRegistry.RegistrationError if an ID is duplicated.
        """
        setdefault = self._handler_classes.setdefault

        for cls in classes:
            if setdefault(cls.type_id, cls) is not cls:
                raise self.RegistrationError(
                    "Duplicated handler's ID (or handler registered twice): {}".format(cls.type_id)
                )

        return self

    def register_operands(self, *classes):
        """Register classes of operand.

        @param classes: Classes inheriting
               <creme_core.core.entity_filter.operands.ConditionDynamicOperand>.
        @return: self (to chain registrations).
        @raises: _EntityFilterRegistry.RegistrationError if an ID is duplicated.
        """
        setdefault = self._operand_classes.setdefault

        for cls in classes:
            if setdefault(cls.type_id, cls) is not cls:
                raise self.RegistrationError(
                    "Duplicated operand's ID (or operand registered twice): {}".format(cls.type_id)
                )

        return self

    def register_operators(self, *classes):
        """Register classes of operator.

        @param classes: Classes inheriting
               <creme_core.core.entity_filter.operators.ConditionOperator>.
        @return: self (to chain registrations).
        @raises: _EntityFilterRegistry.RegistrationError if an ID is duplicated.
        """
        setdefault = self._operator_classes.setdefault

        for cls in classes:
            if setdefault(cls.type_id, cls) is not cls:
                raise self.RegistrationError(
                    "Duplicated operator's ID (or operator registered twice): {}".format(cls.type_id)
                )

        return self

    def get_handler(self, *, type_id, model, name, data):
        """Get an instance of handler from its ID.

        @param type_id: Id of the handler's class
               (see attribute <FilterConditionHandler.type_id>).
        @param model: Class inheriting of <creme_core.models.CremeEntity>.
        @param name: Name of the handler.
        @param data: Data of the handler.
        @return: Instance of a class inheriting <FilterConditionHandler>,
                 or None if the ID is not found, or if data are invalid.
        """
        try:
            cls = self._handler_classes[type_id]
        except KeyError:
            logger.warning(
                '_EntityFilterRegistry.get_handler(): no handler class with type_id="%s" found.',
                type_id,
            )
            return None

        try:
            return cls.build(model=model, name=name, data=data)
        except cls.DataError:
            return None

    def get_operand(self, *, type_id, user):
        """Get an instance of operand from its ID.

        @param type_id: Id of the operand's class
               (see attribute <ConditionDynamicOperand.type_id>).
        @param user: instance of <django.contrib.auth.get_user_model()>
        @return: Instance of a class inheriting <ConditionDynamicOperand>,
                 or None if the ID is invalid or not found.
        """
        cls = self._operand_classes.get(type_id) if isinstance(type_id, str) else None
        return None if cls is None else cls(user)

    def get_operator(self, type_id):
        """Get an instance of operator from its ID.

        @param type_id: Id of the operator's class
               (see attribute <ConditionOperator.type_id>).
        @return: Instance of a class inheriting <ConditionOperator>,
                 or None if the ID is invalid or not found.
        """
        cls = self._operator_classes.get(type_id)
        return None if cls is None else cls()

    @property
    def handler_classes(self):
        """Iterator on registered handler classes."""
        return iter(self._handler_classes.values())

    def operands(self, user):
        """Generator of operand instances."""
        for op_cls in self._operand_classes.values():
            yield op_cls(user)

    @property
    def operators(self):
        """Generator of operator instances."""
        for op_cls in self._operator_classes.values():
            yield op_cls()


entity_filter_registry = _EntityFilterRegistry('Regular filter (usable in list-view...')
credentials_efilter_registry = _EntityFilterRegistry('Credentials filter (internal use)')
