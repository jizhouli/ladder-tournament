#! -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
from datetime import datetime, date, timedelta

from calendar import timegm
from dateutil.tz import tzutc, tzlocal

from .redis_model import FieldValidationError


class Expression(object):

    def eq(self, value):  # ==
        # Creates a condition where the attribute is equal to the value.
        # Attr & Key
        return self.name, 'eq', value

    def ne(self, value):  # !=
        # Creates a condition where the attribute is not equal to the value
        # Attr
        return self.name, 'ne', value

    def lt(self, value):  # <
        # Creates a condition where the attribute is less than the value.
        # Attr & Key
        return self.name, 'lt', value

    def lte(self, value):  # <=
        # Creates a condition where the attribute is less than or
        # equal to the value.
        # Attr & Key
        return self.name, 'lte', value

    def gt(self, value):  # >
        # Creates a condition where the attribute is greater than the value.
        # Attr & Key
        return self.name, 'gt', value

    def gte(self, value):  # >=
        # Creates a condition where the attribute is greater than or equal to
        # the value.
        # Attr & Key
        return self.name, 'gte', value

    def between(self, low_value, high_value):
        # Creates a condition where the attribute is greater than or equal to
        # the low value and less than or equal to the high value.
        # Attr & Key
        return self.name, 'between', (low_value, high_value)

    def in_(self, values):
        # in values is list or tuple
        return self.name, 'in_', values

    def desc(self):
        return self.name, 'desc'

    def asc(self):
        return self.name, 'asc'


class Attribute(Expression):
    """Defines an attribute of the model.
    The attribute accepts strings and are stored in Redis as
    they are - strings.
    Options
        name         -- alternate name of the attribute. This will be used
                        as the key to use when interacting with Redis.
        indexed      -- Index this attribute. Unindexed attributes cannot
                        be used in queries. Default: False.
        index_value  -- Index with this attribute value.
                        Default: False.
        unique       -- validates the uniqueness of the value of the
                        attribute.
        validator    -- a callable that can validate the value of the
                        attribute.
        default      -- Initial value of the attribute.
    """
    def __init__(self,
                 name=None,
                 indexed=False,
                 index_value=False,
                 required=False,
                 validator=None,
                 unique=False,
                 default=None):
        self.name = name
        self.indexed = indexed
        self.index_value = index_value
        self.required = required
        self.validator = validator
        self.default = default
        self.unique = unique

    def __get__(self, instance, owner):
        try:
            return getattr(instance, '_' + self.name)
        except AttributeError:
            if callable(self.default):
                default = self.default()
            else:
                default = self.default
            if not instance:
                return self
            self.__set__(instance, default)
            return default

    def __set__(self, instance, value):
        setattr(instance, '_' + self.name, value)

    def typecast_for_read(self, value):
        """Typecasts the value for reading from Redis."""
        # The redis client encodes all unicode data to utf-8 by default.
        return value.decode('utf-8')

    def typecast_for_storage(self, value):
        """Typecasts the value for storing to Redis."""
        try:
            return unicode(value)
        except UnicodeError:
            return value.decode('utf-8')

    def value_type(self):
        return unicode

    def acceptable_types(self):
        return basestring

    def validate(self, instance):
        val = getattr(instance, self.name)
        errors = []
        # type_validation
        accept_types = self.acceptable_types()
        if val is not None and not isinstance(val, accept_types):
            errors.append((self.name, 'Must be one of %s not a %s' % (str(accept_types), type(val))))
        # validate first standard stuff
        if self.required:
            if val is None or not unicode(val).strip():
                errors.append((self.name, 'required'))
        # validate using validator
        if self.validator:
            r = self.validator(self.name, val)
            if r:
                errors.extend(r)
        if errors:
            raise FieldValidationError(errors)


class CharField(Attribute):

    def __init__(self, max_length=255, **kwargs):
        super(CharField, self).__init__(**kwargs)
        self.max_length = max_length

    def typecast_for_read(self, value):
        if value == b'None':
            return ''
        return value.decode('utf-8')

    def typecast_for_storage(self, value):
        """Typecasts the value for storing to Redis."""
        if value is None:
            return ''
        try:
            return unicode(value)
        except UnicodeError:
            return value.decode('utf-8')

    def validate(self, instance):
        errors = []
        try:
            super(CharField, self).validate(instance)
        except FieldValidationError as err:
            errors.extend(err.errors)

        val = getattr(instance, self.name)

        if errors:
            raise FieldValidationError(errors)

        if val and len(val) > self.max_length:
            errors.append((self.name, 'exceeds max length'))

        if errors:
            raise FieldValidationError(errors)

    def value_type(self):
        return (unicode, str, basestring)

    def acceptable_types(self):
        return self.value_type()


class IntegerField(Attribute):
    def typecast_for_read(self, value):
        return int(value)

    def typecast_for_storage(self, value):
        if value is None:
            return "0"
        return unicode(value)

    def value_type(self):
        return int

    def acceptable_types(self):
        return (int, long)


class FloatField(Attribute):
    def typecast_for_read(self, value):
        return float(value)

    def typecast_for_storage(self, value):
        if value is None:
            return "0"
        return "%f" % value

    def value_type(self):
        return float

    def acceptable_types(self):
        return self.value_type()


class BooleanField(Attribute):
    def typecast_for_read(self, value):
        return bool(int(value))

    def typecast_for_storage(self, value):
        if value is None:
            return "0"
        return "1" if value else "0"

    def value_type(self):
        return bool

    def acceptable_types(self):
        return self.value_type()


class DateTimeField(Attribute):

    def __init__(self, auto_now=False, auto_now_add=False, **kwargs):
        super(DateTimeField, self).__init__(**kwargs)
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add

    def typecast_for_read(self, value):
        try:
            # We load as if the timestampe was naive
            dt = datetime.fromtimestamp(float(value), tzutc())
            # And gently override (ie: not convert) to the TZ to UTC
            return dt
        except TypeError:
            return None
        except ValueError:
            return None

    def typecast_for_storage(self, value):
        if value is None:
            return ''
        if not isinstance(value, datetime):
            raise TypeError("%s should be datetime object, and not a %s" %
                            (self.name, type(value)))
        # Are we timezone aware ? If no, make it TimeZone Local
        if value.tzinfo is None:
            value = value.replace(tzinfo=tzlocal())
        return "%d.%06d" % (float(timegm(value.utctimetuple())),
                            value.microsecond)

    def value_type(self):
        return datetime

    def acceptable_types(self):
        return self.value_type()


class DateField(Attribute):

    def __init__(self, auto_now=False, auto_now_add=False, **kwargs):
        super(DateField, self).__init__(**kwargs)
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add

    def typecast_for_read(self, value):
        try:
            # We load as if it is UTC time
            dt = date.fromtimestamp(float(value))
            # And assign (ie: not convert) the UTC TimeZone
            return dt
        except TypeError:
            return None
        except ValueError:
            return None

    def typecast_for_storage(self, value):
        if value is None:
            return ''
        if not isinstance(value, date):
            raise TypeError("%s should be date object, and not a %s" %
                            (self.name, type(value)))
        return "%d" % float(timegm(value.timetuple()))

    def value_type(self):
        return date

    def acceptable_types(self):
        return self.value_type()


class TimeDeltaField(Attribute):

    def __init__(self, **kwargs):
        super(TimeDeltaField, self).__init__(**kwargs)

    if hasattr(timedelta, "totals_seconds"):
        def _total_seconds(self, td):
            return td.total_seconds
    else:
        def _total_seconds(self, td):
            return (td.microseconds + 0.0 +
                    (td.seconds + td.days * 24 * 3600) * 10 ** 6) / 10 ** 6

    def typecast_for_read(self, value):
        try:
            # We load as if it is UTC time
            if value is None:
                value = 0.
            td = timedelta(seconds=float(value))
            return td
        except TypeError:
            return None
        except ValueError:
            return None

    def typecast_for_storage(self, value):
        if not isinstance(value, timedelta):
            raise TypeError("%s should be timedelta object, and not a %s" %
                            (self.name, type(value)))
        if value is None:
            return None

        return "%d" % self._total_seconds(value)

    def value_type(self):
        return timedelta

    def acceptable_types(self):
        return self.value_type()


class ListField(Attribute):

    def typecast_for_read(self, value):
        if not value:
            return []
        value = json.loads(value)
        return value

    def typecast_for_storage(self, value):
        """Typecasts the value for storing to DynamoDB."""
        if value is None:
            return []
        value = json.dumps(value)
        return value

    def value_type(self):
        return list

    def acceptable_types(self):
        return self.value_type()

    def validate(self, instance):
        errors = []
        try:
            super(ListField, self).validate(instance)
        except FieldValidationError as err:
            errors.extend(err.errors)

        val = getattr(instance, self.name)

        if not isinstance(val, list):
            errors.append((self.name, 'must a list'))

        if errors:
            raise FieldValidationError(errors)


class JsonField(Attribute):

    def typecast_for_read(self, value):
        if not value:
            return []
        value = json.loads(value)
        return value

    def typecast_for_storage(self, value):
        """Typecasts the value for storing to DynamoDB."""
        if value is None:
            return []
        value = json.dumps(value)
        return value

    def value_type(self):
        return (list, dict, str, tuple, int)

    def acceptable_types(self):
        return self.value_type()

    def validate(self, instance):
        errors = []
        try:
            super(JsonField, self).validate(instance)
        except FieldValidationError as err:
            errors.extend(err.errors)

        val = getattr(instance, self.name)

        try:
            json.dumps(val)
        except TypeError:
            errors.append((self.name, 'is not JSON serializable'))

        if errors:
            raise FieldValidationError(errors)


ZINDEXABLE = (IntegerField, DateTimeField, DateField, FloatField)
