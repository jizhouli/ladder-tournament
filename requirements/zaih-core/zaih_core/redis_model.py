#! -*- coding: utf-8 -*-
'''
redis model
修改自 redisco
'''
from __future__ import unicode_literals

import json
from datetime import datetime, date, timedelta

from calendar import timegm
from dateutil.tz import tzutc, tzlocal


__all__ = ['Attribute', 'CharField', 'IntegerField', 'FloatField',
           'DateTimeField', 'DateField', 'TimeDeltaField', 'ListField',
           'ZINDEXABLE', 'BooleanField', 'FieldValidationError',
           'Model']


def redis_setup(_redis):
    global app_redis
    app_redis = _redis


class FieldValidationError(Exception):
    def __init__(self, errors, *args, **kwargs):
        super(FieldValidationError, self).__init__(*args, **kwargs)
        self._errors = errors

    @property
    def errors(self):
        return self._errors

    def __str__(self):
        if self._errors:
            if isinstance(self._errors, list):
                error = self._errors[0]
            else:
                error = self._errors
            return str(error)
        return self._errors


class ParameterError(Exception):

    def __init__(self, errors, *args, **kwargs):
        super(ParameterError, self).__init__(*args, **kwargs)
        self._errors = errors

    @property
    def errors(self):
        return self._errors

    def __str__(self):
        return self._errors


class NotFoundError(Exception):

    def __init__(self, errors, *args, **kwargs):
        super(NotFoundError, self).__init__(*args, **kwargs)
        self._errors = errors

    @property
    def errors(self):
        return self._errors

    def __str__(self):
        return self._errors


class RedisClientError(Exception):

    def __init__(self, errors, *args, **kwargs):
        super(RedisClientError, self).__init__(*args, **kwargs)
        self._errors = errors

    @property
    def errors(self):
        return self._errors

    def __str__(self):
        return self._errors


class Attribute(object):
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


def _get_filter_fields(**kwargs):
    filter_fields = {}
    for field, value in kwargs.iteritems():
        field_and_op = field.split('__')
        if len(field_and_op) == 2:
            _field, op = field_and_op
        else:
            _field, op = field, 'eq'
        filter_fields[_field] = (value, op)
    return filter_fields


def _initialize_attributes(model_class, name, bases, attrs):
    """
    Initialize the attributes of the model.
    """
    model_class._attributes = {}

    # In case of inheritance, we also add the parent's
    # attributes in the list of our attributes
    for parent in bases:
        if not isinstance(parent, ModelBase):
            continue
        for k, v in parent._attributes.iteritems():
            model_class._attributes[k] = v

    for k, v in attrs.iteritems():
        if isinstance(v, Attribute):
            model_class._attributes[k] = v
            v.name = v.name or k


def _initialize_indices(model_class, name, bases, attrs):
    """
    Stores the list of indexed attributes.
    """
    model_class._indexed_fields = []
    model_class._indexed_meta_field = model_class.__index_meta__
    model_class._indexed_unique_fields = model_class.__unique_index__
    model_class._indexed_value_fields = []
    for parent in bases:
        if not isinstance(parent, ModelBase):
            continue
        for k, v in parent._attributes.iteritems():
            if v.indexed:
                model_class._indexed_fields.append(k)

    for k, v in attrs.iteritems():
        if isinstance(v, (Attribute,)):
            if v.indexed:
                model_class._indexed_fields.append(k)
            elif v.index_value:
                model_class._indexed_value_fields.append(k)
    if model_class._meta['indexed_fields']:
        model_class._indexed_fields.extend(model_class._meta['indexed_fields'])


def _initialize_key(model_class, name):
    """
    Initializes the key of the model.
    """
    model_class._key = Key(model_class._meta['key'] or name)


class Key(unicode):

    def __getitem__(self, key):
        if self:
            return Key(u"%s:%s" % (self, key))
        else:
            return Key(u"%s" % key)


class Pipe(object):
    _p = None

    @property
    def pipeline(self):
        if self._p is None:
            self._p = app_redis.pipeline(transaction=False)
        return self._p

    def commit(self):
        """
        Saves the instance to the datastore with the following steps:
        """
        return self.pipeline.execute()

    def add(self, instance):
        if not instance.is_valid():
            errors = instance._errors
            raise FieldValidationError(errors)
        params = instance.attributes_dict
        storage_params = {}
        for att in params:
            descriptor = instance.attributes[att]
            storage_params[att] = descriptor.typecast_for_storage(
                getattr(instance, att))
        self.pipeline.hmset(instance.key(), storage_params)
        self._add_to_indices(instance)

    def _add_to_indices(self, instance):
        """Adds the base64 encoded values of the indexed fields."""
        for att in instance.indexed_fields:
            self._add_to_index(instance, att)

    def update(self, instance, **kwargs):
        '''
        1. find need delete indexes
        '''
        indexed_value_fields = []
        _indexed_value_fields = instance._indexed_value_fields
        for k, v in kwargs.iteritems():
            if k in _indexed_value_fields and v != getattr(instance, k):
                indexed_value_fields.append(k)
        if indexed_value_fields:
            self._delete_from_unique_fields(
                instance, indexed_value_fields=indexed_value_fields)
        params = instance.update_attributes(**kwargs)
        if not instance.is_valid():
            raise FieldValidationError(instance._errors)
        # update index
        instance._initialize_indexed_keys()
        storage_params = {}
        for att in params:
            descriptor = instance.attributes[att]
            storage_params[att] = descriptor.typecast_for_storage(
                getattr(instance, att))
        self.pipeline.hmset(instance.key(), storage_params)
        self._update_indices(instance, params)

    def _update_indices(self, instance, params):
        """Updates the indices of the object."""
        # self._delete_from_indices(instance)
        for attr in params.keys():
            if attr in instance.indexed_fields:
                self._add_to_index(instance, attr)
            elif attr in instance._indexed_value_fields:
                self._add_to_indices(instance)

    def delete(self, instance):
        self._delete_from_indices(instance)
        self.pipeline.delete(instance.key())

    def _add_to_index(self, instance, att, val=None):
        """
        Adds the id to the index.
        This also adds to the _indices set of the object.
        """
        index = instance.indices[att]
        if index is None:
            return
        t, index = index
        if t == 'attribute':
            self.pipeline.sadd(index, instance.id)
            self.pipeline.sadd(instance.key()['_indices'], index)
        elif t == 'sortedset':
            zindex, zindex_with_base, zindex_unique = index
            descriptor = instance.attributes[att]
            score = descriptor.typecast_for_storage(getattr(instance, att))
            self.pipeline.zadd(zindex, score, instance.id)
            self.pipeline.zadd(zindex_with_base, score, instance.id)
            for unique_index in zindex_unique:
                # add unique index
                self.pipeline.zadd(unique_index, score, instance.id)
                self.pipeline.sadd(instance.key()['_zindex_unique'], unique_index)
            self.pipeline.sadd(instance.key()['_zindices'], zindex)
            self.pipeline.sadd(instance.key()['_zindices_with_meta'], zindex_with_base)

    def _delete_from_unique_fields(self, instance, indexed_value_fields=None):
        for attr in instance.indexed_fields:
            index = instance._indices[attr]
            t, index = index
            if t == 'sortedset':
                zindex, zindex_with_base, zindex_unique = index
                for unique_index in zindex_unique:
                    for iv_field in indexed_value_fields:
                        if unique_index.find(iv_field):
                            self.pipeline.zrem(unique_index, instance.id)
                            self.pipeline.srem(instance.key()['_zindex_unique'], unique_index)

    def _delete_from_indices(self, instance):
        """
        Deletes the object's id from the sets(indices) it has been added
        to and removes its list of indices (used for housekeeping).
        """
        for attr in instance.indexed_fields:
            index = instance._indices[attr]
            t, index = index
            if t == 'attribute':
                self.pipeline.srem(index, instance.id)
                self.pipeline.srem(instance.key()['_indices'], index)
            elif t == 'sortedset':
                zindex, zindex_with_base, zindex_unique = index
                self.pipeline.zrem(zindex, instance.id)
                self.pipeline.zrem(zindex_with_base, instance.id)
                for unique_index in zindex_unique:
                    # add unique index
                    self.pipeline.zrem(unique_index, instance.id)
                    self.pipeline.srem(instance.key()['_zindex_unique'], unique_index)
                self.pipeline.srem(instance.key()['_zindices'], zindex)
                self.pipeline.srem(instance.key()['_zindices_with_base'], zindex_with_base)
        return

    def get_data(self, instance):
        self.pipeline.hgetall(instance.key())


class ModelOptions(object):
    """Handles options defined in Meta class of the model.
    Example:
    >>> from zaih_core.redis_index import Model
    >>> import redis
    >>> class Person(Model):
    ...     name = Attribute()
    ...     class Meta:
    ...         indices = ('full_name',)
    ...         db = redis.Redis(host='localhost', port=29909)
    """
    def __init__(self, meta):
        self.meta = meta

    def get_field(self, field_name):
        if self.meta is None:
            return None
        try:
            return self.meta.__dict__[field_name]
        except KeyError:
            return None
    __getitem__ = get_field


class ModelBase(type):

    """
    Metaclass of the Model.
    """

    __model_name__ = None
    __index_meta__ = None
    __unique_index__ = []

    def __init__(cls, name, bases, attrs):
        super(ModelBase, cls).__init__(name, bases, attrs)
        cls._meta = ModelOptions(attrs.pop('Meta', None))
        name = cls.__model_name__ or name
        _initialize_attributes(cls, name, bases, attrs)
        _initialize_indices(cls, name, bases, attrs)
        _initialize_key(cls, name)


class Model(object):

    __metaclass__ = ModelBase
    __redis_client__ = None

    def __init__(self, **kwargs):
        self.update_attributes(**kwargs)
        self._initialize_indexed_keys()
        self.filter_fields_dict = {}  # must index_value or indexed is True
        self.filter_fields = []  # must index_value is True
        self.order_by_key = None
        self.indexed_key = None
        self.desc = False
        self._pipe = Pipe()

    def is_valid(self):
        """
        Returns True if all the fields are valid, otherwise
        errors are in the 'errors' attribute
        It first validates the fields (required, unique, etc.)
        and then calls the validate method.
        >>> from zaih_core.redis_index import Model
        >>> def validate_me(field, value):
        ...     if value == "Invalid":
        ...         return (field, "Invalid value")
        ...
        >>> class Foo(Model):
        ...     bar = Attribute(validator=validate_me)
        ...
        >>> f = Foo()
        >>> f.bar = "Invalid"
        >>> f.save()
        False
        >>> f.errors
        ['bar', 'Invalid value']
        .. WARNING::
            You may want to use ``validate`` described below to validate your model
        """
        self._errors = []
        for field in self.fields:
            try:
                field.validate(self)
            except FieldValidationError as e:
                self._errors.extend(e.errors)
        self.validate()
        return not bool(self._errors)

    def validate_attrs(self, **kwargs):
        self._errors = []
        for attr, value in kwargs.iteritems():
            field = self.attributes.get(attr)
            try:
                field.validate(self)
            except FieldValidationError as e:
                self._errors.extend(e.errors)
        return not bool(self._errors)

    def validate(self):
        """
        Overriden in the model class.
        The function is here to help you validate your model.
        The validation should add errors to self._errors.
        Example:
        >>> from zaih_core.redis_index import Model
        >>> class Foo(Model):
        ...     name = Attribute(required=True)
        ...     def validate(self):
        ...         if self.name == "Invalid":
        ...             self._errors.append(('name', 'cannot be Invalid'))
        ...
        >>> f = Foo(name="Invalid")
        >>> f.save()
        False
        >>> f.errors
        [('name', 'cannot be Invalid')]
        """
        pass

    def update_attributes(self, **kwargs):
        """
        Updates the attributes of the model.
        >>> class Foo(Model):
        ...    name = Attribute()
        ...    title = Attribute()
        ...
        >>> f = Foo(name="Einstein", title="Mr.")
        >>> f.update_attributes(name="Tesla")
        >>> f.name
        'Tesla'
        """
        params = {}
        attrs = self.attributes.values()
        for att in attrs:
            if att.name in kwargs:
                att.__set__(self, kwargs[att.name])
                params[att.name] = kwargs[att.name]
        return params

    def _get_values_for_read(self, values):
        read_values = {}
        for att, value in values.iteritems():
            if att not in self.attributes:
                continue
            descriptor = self.attributes[att]
            _value = descriptor.typecast_for_read(value)
            read_values[att] = _value
        return read_values

    @classmethod
    def get_by_id(cls, id):
        instance = cls(id=id)
        instance._pipe.get_data(instance)
        values = instance._pipe.commit()
        values = filter(lambda x: x, values)
        if not values:
            return None
        read_values = instance._get_values_for_read(values[0])
        return cls(**read_values)

    @classmethod
    def batch_get_by_id(cls, ids):
        if not isinstance(ids, (list, tuple)):
            raise ParameterError('Ids must list or tuple')
        _pipe = Pipe()
        instances = []
        _instances = []
        for id in ids:
            instance = cls(id=id)
            _pipe.get_data(instance)
            _instances.append(instance)
        values = _pipe.commit()
        for i, value in enumerate(values):
            if not value:
                instance = None
            else:
                read_value = _instances[i]._get_values_for_read(value)
                instance = cls(**read_value)
            instances.append(instance)
        return instances

    def key(self, att=None):
        """
        Returns the Redis key where the values are stored.
        >>> class Foo(Model):
        ...    name = Attribute()
        ...    title = Attribute()
        ...
        >>> f = Foo(name="Einstein", title="Mr.")
        >>> f.save()
        True
        >>> f.key() == "%s:%s" % (f.__class__.__name__, f.id)
        True
        """
        key = self._key
        if self.id is not None:
            key = key[self.id]
        if att is not None:
            key = key[att]
        return key

    @classmethod
    def create(cls, **kwargs):
        """
        1. Validate all the fields
        # 2. Assign an ID if the object is new
        3. Save to the datastore.
        """
        instance = cls(**kwargs)
        instance._pipe.add(instance)
        instance._pipe.commit()
        return instance

    def update(self, **kwargs):
        self._pipe.update(self, **kwargs)
        self._pipe.commit()
        return self

    def delete(self):
        """Deletes the object from the datastore."""
        self._pipe.delete(self)
        self._pipe.commit()

    @classmethod
    def filter_by(cls, **kwargs):
        # indexed=True or index_value=True
        filter_fields_dict = _get_filter_fields(**kwargs)
        _filter_fields_dict = {k: v[0] for k, v in
                               filter_fields_dict.iteritems()}
        instance = cls(**_filter_fields_dict)
        if not instance.validate_attrs(**_filter_fields_dict):
            errors = instance._errors
            raise FieldValidationError(errors)
        for attr, value in _filter_fields_dict.iteritems():
            value_and_op = filter_fields_dict[attr]
            _, op = value_and_op
            if attr in instance._indexed_fields:
                if not instance.filter_fields_dict:
                    descriptor = instance.attributes[attr]
                    value = descriptor.typecast_for_storage(getattr(instance, attr))
                    instance.filter_fields_dict[attr] = (value, op)
                else:
                    raise FieldValidationError('Filter field must only one')
            elif attr in instance._indexed_value_fields:
                if op == 'eq':
                    instance.filter_fields.append(attr)
                else:
                    raise FieldValidationError('%s: only support "="' % attr)
            else:
                raise FieldValidationError('%s: not indexed value' % attr)
        return instance

    def order_by(self, field, desc=False):
        '''
        fields = field + filter_fields
        1. 如果fields 只有一个值 那么 索引只用这一个
        例如: feed:date_created
        2. 如果fields 有大于1个值:
            * 如果有meta_field(索引+meta_field) 索引为meta+attr
            例如: feed:account_id:1000:date_created
            * 如果没有meta_field 判断是不是联合索引
            例如：feed:account_id:1000:action:update:date_created
        '''
        if field not in self._indexed_fields:
            raise FieldValidationError('%s not indexed field' % field)
        self.order_by_key = field
        fields = set([field])
        for attr in self.filter_fields:
            fields.add(attr)
        self.desc = desc
        fields_len = len(fields)
        meta_field = self._indexed_meta_field
        if fields_len == 1:
            self.indexed_key = self._indexed_key_for_attr(field)
        elif fields_len == 2 and meta_field in fields:
            self.indexed_key = self._indexed_key_for_attr_with_meta(field)
        else:
            # 对比所有联合索引
            unique_attrs = self._indexed_unique_fields
            for attrs in unique_attrs:
                if set(attrs) == fields:
                    self.indexed_key = self._indexed_key_for_unique(attrs)
        if not self.indexed_key:
            raise FieldValidationError('%s not indexed field' % str(list(fields)))
        return self

    def count(self, start='-inf', end='+inf'):
        '''
        return indexed_key count
        '''
        counts = app_redis.zcount(self.indexed_key, start, end)
        return counts

    def list(self, offset=0, limit=20):
        '''
        eq     EqFilter    key = value
        neq    NeqFilter   key != value
        lt     LtFilter    key < value
        lte    LteFilter   key <= value
        gt     GtFilter    key > value
        gte    GteFilter   key >= value
        '''
        pipeline = app_redis.pipeline(transaction=False)
        filter_value_and_op = self.filter_fields_dict.get(self.order_by_key)
        if filter_value_and_op:
            filter_value, op = filter_value_and_op
        else:
            filter_value, op = None, None
        if not filter_value:
            start = offset
            end = limit + offset - 1
            if self.desc:
                pipeline.zrevrange(self.indexed_key, start, end)
            else:
                pipeline.zrange(self.indexed_key, start, end)
        else:
            args = [self.indexed_key, 'max', 'min']
            kwargs = {'start': offset, 'num': limit}
            if op in ['lt', 'gt']:
                filter_value = '(%s' % filter_value
            if op == 'eq':
                args[1], args[2] = filter_value, filter_value
            elif op in ('lt', 'lte'):
                args[1], args[2] = str(filter_value), '-inf'
            elif op in ('gt', 'gte'):
                args[1], args[2] = '+inf', filter_value
            if self.desc:
                pipeline.zrevrangebyscore(*args, **kwargs)
            else:
                pipeline.zrangebyscore(*args, **kwargs)
        values = pipeline.execute()
        ids = values[0]
        keys = [self.key(id) for id in ids]
        for key in keys:
            pipeline.hgetall(key)
        mvalues = pipeline.execute()
        read_mvalues = []
        for values in mvalues:
            if not values:
                continue
            read_values = self._get_values_for_read(values)
            ov = self.__class__(**read_values)
            read_mvalues.append(ov)
        return read_mvalues

    @property
    def attributes_dict(self):
        """
        Returns the mapping of the model attributes and their
        values.
        >>> from zaih_core.redis_index import Model
        >>> class Foo(Model):
        ...    name = Attribute()
        ...    title = Attribute()
        ...
        >>> f = Foo(name="Einstein", title="Mr.")
        >>> f.attributes_dict
        {'name': 'Einstein', 'title': 'Mr.'}
        .. NOTE: the key ``id`` is present *only if* the object has been saved before.
        """
        h = {}
        for k in self.attributes.keys():
            h[k] = getattr(self, k)
        if 'id' not in self.attributes.keys() and not self.is_new():
            h['id'] = self.id
        return h

    @property
    def id(self):
        """Returns the id of the instance.
        Raises MissingID if the instance is new.
        """
        if not hasattr(self, '_id'):
            raise FieldValidationError('missingid')
        return self._id

    @id.setter
    def id(self, val):
        """
        Setting the id for the object will fetch it from the datastorage.
        """
        self._id = str(val)
        stored_attrs = self.db.hgetall(self.key())
        attrs = self.attributes.values()
        for att in attrs:
            if att.name in stored_attrs:
                att.__set__(self, att.typecast_for_read(stored_attrs[att.name]))

    @property
    def attributes(self):
        """Return the attributes of the model.
        Returns a dict with models attribute name as keys
        and attribute descriptors as values.
        """
        return dict(self._attributes)

    @property
    def fields(self):
        """Returns the list of field names of the model."""
        return self.attributes.values()

    @property
    def indices(self):
        """
        Return a list of the indexed fields of the model.
        ie: all attributes with indexed=True.
        """
        return self._indices

    @property
    def indexed_fields(self):
        """
        Return a list of the indexed fields of the model.
        ie: all attributes with indexed=True.
        """
        return self._indexed_fields

    def _initialize_indexed_keys(self):
        indices = {}
        for att in self.indexed_fields:
            index = self._indexed_key_for(att)
            indices[att] = index
        self._indices = indices
        return indices

    def _indexed_key_for(self, att, value=None):
        """Returns a key based on the attribute and its value.
        The key is used for indexing.
        """
        if value is None:
            value = getattr(self, att)
            if callable(value):
                value = value()
        if value is None:
            return None
        return self._get_indexed_key_for_non_list_attr(att, value)

    def _get_indexed_key_for_non_list_attr(self, att, value):
        descriptor = self.attributes.get(att)
        if descriptor and isinstance(descriptor, ZINDEXABLE):
            sval = descriptor.typecast_for_storage(value)
            return self._tuple_for_indexed_key_attr_zset(att, value, sval)
        elif descriptor:
            val = descriptor.typecast_for_storage(value)
            return self._tuple_for_indexed_key_attr_val(att, val)
        else:
            # this is non-attribute index defined in Meta
            return self._tuple_for_indexed_key_attr_val(att, value)

    def _tuple_for_indexed_key_attr_val(self, att, val):
        return ('attribute', self._indexed_key_for_attr_val(att, val))

    def _tuple_for_indexed_key_attr_zset(self, att, val, sval):
        return ('sortedset',
                (self._indexed_key_for_attr(att),
                 self._indexed_key_for_attr_with_meta(att),
                 self._indexed_key_for_unique_attrs(att)))

    def _get_attr_value(self, attr):
        meta_value = getattr(self, attr)
        if callable(meta_value):
            meta_value = meta_value()
        base_descriptor = self.attributes.get(attr)
        value = base_descriptor.typecast_for_storage(meta_value)
        return value

    def _indexed_key_for_attr_with_meta(self, attr):
        field = self._indexed_meta_field
        if not field:
            return None
        value = self._get_attr_value(field)
        base_key = Key()
        key = base_key[field][value]
        return self._key[key][attr]

    def _indexed_key_for_unique_attrs(self, att):
        unique_attrs = self._indexed_unique_fields
        unique_indies = []
        for attrs in unique_attrs:
            if att not in attrs:
                continue
            key = self._indexed_key_for_unique(attrs)
            unique_indies.append(key)
        return unique_indies

    def _indexed_key_for_unique(self, attrs):
        indexed_value_fields = set(self._indexed_value_fields)
        unique_key = Key()
        for attr in attrs:
            if attr in indexed_value_fields:
                value = self._get_attr_value(attr)
                unique_key = unique_key[attr][value]
        key = self._key[unique_key][attr]
        return key

    def _indexed_key_for_attr(self, attr):
        return self._key[attr]

    def _indexed_key_for_attr_val(self, att, val):
        self._indexed_key_for_attr_with_meta(att)
        return self._key[att][val]
