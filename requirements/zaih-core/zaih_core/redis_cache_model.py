#! -*- coding: utf-8 -*-
'''
redis cache model

model 需要定义的参数为
__expire__              key的过期时间，-1 为不设置过期时间
__model_name__          model name
__redis_client__        redis client
__refresh_frequency__   刷新频率

cache model key 的生成逻辑为

如果有设置过期时间:

1. 判断过期时间，如果过期时间超过1天，会自动生成一个按天分隔 索引 key
                且key 的过期时间设置为 __expire__ 的3倍 # 冗余两倍时间

   比如： __expire__ = 86400 * 7  设置七天有效期
   index_key = 'notice:account_id:123:date_created'  过期时间为 7 天
   自动生成的2级索引 index_key2 = 'notice:account_id:123:date_created/2408'
   2408 = timestamp/(86400*7)

2. 取数据时，先从 index_key = 'notice:account_id:123:date_created' 的索引中取值
   如果没有这个索引，合并最新两个 index_key2 到 index_key

3. 存数据时，如果有 需要只把数据存入 index_key2 中,
如果index_key 已经生成了也需要存到 index_key（应用场景，查出数据后同时更新当前key)
'''

from __future__ import unicode_literals

import time
import copy
import itertools
from datetime import datetime

from .coding import smart_str
from .redis_model import FieldValidationError, ParameterError
from .redis_cache_fields import Attribute, ZINDEXABLE

__all__ = ['CacheModel']


class IntegrityError(Exception):
    def __init__(self, errors, *args, **kwargs):
        super(IntegrityError, self).__init__(*args, **kwargs)
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


def _get_index_number(expire, created_at=None):
    if not created_at:
        timestamp = time.time()
    else:
        at = smart_str(created_at)
        timestamp = float(at)
    if expire > 86400 * 7:
        # 如果过期时间超过7天 按七天分隔
        seconds = 86400 * 7
    elif expire > 86400:
        # 如果过期时间超过1天 按1天分隔
        seconds = 86400
    else:
        seconds = 3600
    # 要多两个周期才能覆盖完整数据
    # 比如 过期时间为10天 expire/seconds = 1
    # 需要 当前 key 和 过去两周的 key 才能覆盖10天的数据
    return int(timestamp/seconds), int(expire/seconds) + 2


def _get_expire_key(key, expire, created_at=None):
    # 如果不设置过期时间 expire_key = None
    if expire == -1:
        return None, expire
    number, _ = _get_index_number(expire, created_at)
    expire_key = '{key}/{num}'.format(key=key, num=number)
    return expire_key, expire * 3


def _get_recent_indexes(key, expire):
    number, times = _get_index_number(expire)
    indexes = []
    for i in range(times):
        index = '{key}/{num}'.format(key=key, num=number-i)
        indexes.append(index)
    return indexes


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


def _initialize_indexes(model_class, name, bases, attrs):
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


class ModelOptions(object):
    """
    Handles options defined in Meta class of the model.
    Example:

        from zaih_core.redis_index import Model
        import redis
        class Person(Model):
            name = Attribute()
            class Meta:
                indexes = ('full_name',)
                db = redis.Redis(host='localhost', port=29909)
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
        _initialize_indexes(cls, name, bases, attrs)
        _initialize_key(cls, name)


class CacheModel(object):

    __metaclass__ = ModelBase

    __model_name__ = None
    __expire__ = -1  # key的过期时间，-1 为不设置过期时间
    __created_at__ = None  # 改数据所创建的时间 用于确定 expire_key
    __redis_client__ = None

    def __init__(self, **kwargs):
        self.update_attributes(**kwargs)
        self._initialize_indexed_keys()
        self.filter_fields = []  # must index_value is True
        self.order_by_key = None
        self.indexed_key = None
        self.desc = False

    def update_attributes(self, **kwargs):
        """
        Updates the attributes of the model.
            class Foo(Model):
               name = Attribute()
               title = Attribute()

            f = Foo(name="Einstein", title="Mr.")
            f.update_attributes(name="Tesla")
            f.name
            'Tesla'
        """
        params = {}
        attrs = self.attributes.values()
        for att in attrs:
            if att.name in kwargs:
                att.__set__(self, kwargs[att.name])
                params[att.name] = kwargs[att.name]
        return params

    @property
    def attributes_dict(self):
        """
        Returns the mapping of the model attributes and their
        values.
            from zaih_core.redis_index import Model
            class Foo(Model):
               name = Attribute()
               title = Attribute()

            f = Foo(name="Einstein", title="Mr.")
            f.attributes_dict
        {'name': 'Einstein', 'title': 'Mr.'}
        .. NOTE: the key ``id`` is present *only if*
        the object has been saved before.
        """
        h = {}
        for k in self.attributes.keys():
            h[k] = getattr(self, k)
        if 'id' not in self.attributes.keys() and not self.is_new():
            h['id'] = self.id
        return h

    def is_valid(self):
        """
        Returns True if all the fields are valid, otherwise
        errors are in the 'errors' attribute
        It first validates the fields (required, unique, etc.)
        and then calls the validate method.
        """
        self._errors = []
        for field in self.fields:
            try:
                field.validate(self)
            except FieldValidationError as e:
                self._errors.extend(e.errors)
        is_value, errors = self.validate()
        return is_value

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
        """
        return not bool(self._errors), self._errors

    def _get_values_for_read(self, values):
        read_values = {}
        for att, value in values.iteritems():
            if att not in self.attributes:
                continue
            descriptor = self.attributes[att]
            _value = descriptor.typecast_for_read(value)
            read_values[att] = _value
        return read_values

    def _get_values_for_storage(self, attr, value):
        descriptor = self.attributes[attr]
        score = descriptor.typecast_for_storage(value)
        return score

    def _get_zindex_buckets(self, *zindexes):
        zindex_buckets = {}
        for zindex, bucket in zindexes:
            if isinstance(zindex, (str, unicode)):
                zindex_buckets[zindex] = bucket
            elif isinstance(zindex, (list, tuple)):
                for index in zindex:
                    zindex_buckets[index] = bucket
        return zindex_buckets

    def _add_to_indexes(self, instance, created_at=None):
        """Adds the base64 encoded values of the indexed fields."""
        for att in instance.indexed_fields:
            self._add_to_index(instance, att, created_at=created_at)

    def _add_to_index(self, instance, att, val=None, created_at=None):
        """
        Adds the id to the index.
        This also adds to the _indexes set of the object.
        """
        index = instance.indexes[att]
        if index is None:
            return
        t, index = index
        if t == 'attribute':
            pass
            # self.pipeline.sadd(index, instance.id)
            # self.pipeline.sadd(instance.key()['_indexes'], index)
        elif t == 'sortedset':
            zindex, zindex_with_base, zindex_unique = index
            descriptor = instance.attributes[att]
            score = descriptor.typecast_for_storage(getattr(instance, att))
            all_indexes = [zindex, zindex_with_base]
            all_indexes.extend(zindex_unique)
            # 先判断索引是否存在
            with instance.__redis_client__.pipeline(transaction=False) as p:
                for i in all_indexes:
                    p.exists(i)
                all_exists = p.execute()
            indexes_exists = dict(zip(all_indexes, all_exists))
            zindex_buckets = self._get_zindex_buckets(
                (zindex, '_zindexes'),
                (zindex_with_base, '_zindex_with_meta'),
                (zindex_unique, '_zindex_unique'))
            # 将数据加到 二级索引
            with instance.__redis_client__.pipeline(transaction=False) as p:
                for zindex in all_indexes:
                    expire_key, expire = _get_expire_key(zindex,
                                                         instance.__expire__,
                                                         created_at)
                    if expire_key:
                        p.zadd(expire_key, score, instance.id)
                        p.expire(expire_key, expire)
                    # 将数据添加到一级索引（现在不加，在取值的时候合成）
                    bucket = zindex_buckets[zindex]
                    is_store = indexes_exists[zindex]
                    self._save_to_index(expire_key, expire, p,
                                        instance, zindex, score,
                                        bucket, created_at, is_store)
                p.execute()

    def _save_to_index(self, expire_key, expire, p, instance,
                       index, score, bucket,
                       created_at=None, is_store=False):
        '''
        :param expire_key:  expire_key 二级索引
        :param expire:  expire 过期时间
        :param p:  redis pipeline
        :param instance: instance
        :param index:  index name
        :param score:  index score
        :param bucket: index bucket
        :param created_at: created time 用于确认二级索引
        :param is_store: 是否保存数据到 index
        :return:
        '''
        bucket_key = instance.key()[bucket]
        if not expire_key or is_store:
            p.zadd(index, score, instance.id)
            p.sadd(bucket_key, index)
        if expire > 0:
            p.expire(index, expire)
            p.expire(bucket_key, expire)

    def add(self, instance, update=False):
        values = instance.__redis_client__.hgetall(instance.key())
        if values and not update:
            raise IntegrityError('duplicate key value violates unique constraints <id> id: %s already exists.' % instance.id)
        if not instance.is_valid():
            errors = instance._errors
            raise FieldValidationError(errors)
        params = instance.attributes_dict
        storage_params = {}
        for att in params:
            descriptor = instance.attributes[att]
            storage_params[att] = descriptor.typecast_for_storage(
                getattr(instance, att))
        # 添加数据所属时间
        created_at_name = instance.__created_at__
        if created_at_name:
            created_at = storage_params[created_at_name]
        else:
            created_at = datetime.now()
        storage_params['_created_at'] = created_at
        with instance.__redis_client__.pipeline(transaction=False) as p:
            p.hmset(instance.key(), storage_params)
            if instance.__expire__ > 0:
                p.expire(instance.key(), instance.__expire__ * 3)
            p.execute()
        if not update:
            self._add_to_indexes(instance, created_at)

    @classmethod
    def create(cls, **kwargs):
        """
        1. Validate all the fields
        2. Assign an ID if the object is new
        3. Save to the datastore.
        """
        instance = cls(**kwargs)
        instance.add(instance)
        return instance

    def save(self):
        self.add(self)
        return self

    def update(self, **kwargs):
        # first delete
        params = self.attributes_dict
        params.update(kwargs)
        if (set(self.indexed_fields) | set(self.indexed_value_fields)) & set(kwargs.keys()):
            self.delete()
            update = False
        else:
            update = True
        instance = self.__class__(**params)
        self.add(instance, update=update)
        return instance

    def delete(self):
        '''
        delete all zindex
        :return: True
        '''
        with self.__redis_client__.pipeline(transaction=False) as p:
            created_at_name = self.__created_at__
            if created_at_name:
                value = self.attributes_dict.get(created_at_name)
                if value:
                    created_at = self._get_values_for_storage(
                        created_at_name, value)
                else:
                    created_at = None
            else:
                created_at = None
            for attr in self.indexed_fields:
                index = self._indexes[attr]
                t, index = index
                if t == 'attribute':
                    pass
                elif t == 'sortedset':
                    zindex, zindex_with_base, zindex_unique = index
                    zindex_buckets = self._get_zindex_buckets(
                        (zindex, '_zindexes'),
                        (zindex_with_base, '_zindex_with_meta'),
                        (zindex_unique, '_zindex_unique'))
                    for zindex, _bucket in zindex_buckets.items():
                        p.zrem(zindex, self.id)
                        expire_key, expire = _get_expire_key(
                            zindex, self.__expire__, created_at)
                        p.zrem(expire_key, self.id)
                        bucket = self.key()[_bucket]
                        p.srem(bucket, zindex)
            p.delete(self.key())
            p.execute()
        return True

    @classmethod
    def get_by_id(cls, id):
        instance = cls(id=id)
        values = instance.__redis_client__.hgetall(instance.key())
        if not values:
            return None
        read_values = instance._get_values_for_read(values)
        return cls(**read_values)

    @classmethod
    def batch_get_by_ids(cls, ids):
        if not isinstance(ids, (list, tuple)):
            raise ParameterError('Ids must list or tuple')
        if not ids:
            return []
        instance = cls(id=ids[0])
        with instance.__redis_client__.pipeline(transaction=False) as p:
            for id in ids:
                instance = cls(id=id)
                p.hgetall(instance.key())
            values = p.execute()
        # values = filter(lambda x: x, values)
        results = []
        for value in values:
            if value:
                result = cls(id=value['id'])
                results.append(cls(**result._get_values_for_read(value)))
            else:
                results.append(None)
        return results

    def key(self, att=None):
        """
        Returns the Redis key where the values are stored.
            class Foo(Model):
               name = Attribute()
               title = Attribute()

            f = Foo(name="Einstein", title="Mr.")

        f.save()
        True

            f.key() == "%s:%s" % (f.__class__.__name__, f.id)
        True
        """
        key = self._key
        if self.id is not None:
            key = key[self.id]
        if att is not None:
            key = key[att]
        return key

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
    def expire_indexes(self):
        # 可以过期的索引 即二级索引
        results = {}
        for field in self._indexed_fields:
            indexes = self._indexes[field]
            t, index = indexes
            _zindexes = []
            if t == 'sortedset':
                zindex, zindex_with_base, zindex_unique = index
                ezindex, _ = _get_expire_key(zindex, self.__expire__,
                                             self._created_at)
                ezindex_with_base, _ = _get_expire_key(zindex_with_base,
                                                       self.__expire__,
                                                       self._created_at)
                _zindexes = [ezindex, ezindex_with_base]
                _uzindex = []
                for zu in zindex_unique:
                    ezu, _ = _get_expire_key(zu, self.__expire__,
                                             self._created_at)
                    _uzindex.append(ezu)
                _zindexes.append(_uzindex)
                # print field, t, _zindexes
                results[field] = (t, _zindexes)
        return results

    @property
    def indexes(self):
        """
        Return a list of the indexed fields of the model.
        ie: all attributes with indexed=True.
        """
        return self._indexes

    @property
    def indexed_fields(self):
        """
        Return a list of the indexed fields of the model.
        ie: all attributes with indexed=True.
        """
        return self._indexed_fields

    @property
    def indexed_value_fields(self):
        """
        Return a list of the indexed value fields of the model.
        ie: all attributes with index_value=True.
        """
        return self._indexed_value_fields

    def _initialize_indexed_keys(self):
        indexes = {}
        for att in self.indexed_fields:
            index = self._indexed_key_for(att)
            if index:
                indexes[att] = index
        self._indexes = indexes
        return indexes

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
        return

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
        return value, meta_value

    def _indexed_key_for_attr_with_meta(self, attr):
        field = self._indexed_meta_field
        if not field:
            return None
        value, _ = self._get_attr_value(field)
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
        unique_key = Key()
        for attr in attrs:
            if attr in self.indexed_value_fields:
                value, _ = self._get_attr_value(attr)
                unique_key = unique_key[attr][value]
        key = self._key[unique_key][attr]
        return key

    def _get_indexed_key_for_unique(self, attrs):
        # 只在查询的时候使用 查询的时候可能会用到 in_ 操作
        unique_key = Key()
        unique_key_dict = {}
        order_attr = None
        for attr in attrs:
            if attr in self.indexed_value_fields:
                value, value_meta = self._get_attr_value(attr)
                unique_key = unique_key[attr]['{%s}' % attr]
                if isinstance(value_meta, (list, tuple)):
                    values = []
                    for v in value_meta:
                        _value = self._get_values_for_storage(attr, v)
                        values.append(_value)
                else:
                    values = [value]
                for v in values:
                    unique_key_dict.setdefault(attr, []).append({attr: v})
            else:
                order_attr = attr
        # {u'is_read': [{u'is_read': u'0'}], u'receiver_id': [{u'receiver_id':
        # u'2'}, {u'receiver_id': u'4'}]}
        # to
        # [({u'is_read': u'0'}, {u'receiver_id': u'2'}), ({u'is_read': u'0'},
        # {u'receiver_id': u'4'})]
        unique_key_result = []
        for uk in itertools.product(*unique_key_dict.values()):
            unique_key_result.append(uk)
        keys = []
        key_tpl = self._key[unique_key][order_attr]
        for unique_kv in unique_key_result:
            params = {}
            for kv in unique_kv:
                params.update(kv)
            keys.append(key_tpl.format(**params))
        return keys

    def _indexed_key_for_attr(self, attr):
        return self._key[attr]

    def _indexed_key_for_attr_val(self, att, val):
        self._indexed_key_for_attr_with_meta(att)
        return self._key[att][val]

    @classmethod
    def query(cls):
        query = Query(cls)
        return query


class Query(object):

    def __init__(self, model_class):
        self.instance = None
        self.model_class = model_class
        self.filter_fields_op_dict = {}  # must index_value or indexed is True
        self.filter_fields_value_dict = {}  # must index_value or indexed is True
        self.sort_key = None
        self.sort_dict = {}
        self.indexed_field = None
        self.indexed_key = None
        self._offset = 0
        self._limit = 100

    def _validate_params(self, **kwargs):
        instance = self.model_class(**kwargs)
        if not instance.validate_attrs(**kwargs):
            errors = instance._errors
            raise FieldValidationError(errors)

    def filter(self, arg):
        field_name, op, value = arg
        if op == 'in_' and isinstance(value, (list, tuple)):
            for v in value:
                self._validate_params(**{field_name: v})
        else:
            self._validate_params(**{field_name: value})
        self.filter_fields_op_dict[field_name] = (value, op)
        self.filter_fields_value_dict[field_name] = value
        query = copy.deepcopy(self)
        return query

    def filter_by(self, *args):
        # indexed=True or index_value=True
        params = {}
        for arg in args:
            field_name, op, value = arg
            params[field_name] = value
            self.filter_fields_op_dict[field_name] = (value, op)
            self.filter_fields_value_dict[field_name] = value
        self._validate_params(**params)
        query = copy.deepcopy(self)
        return query

    def _validate_filter_values(self):
        for attr, value in self.filter_fields_value_dict.iteritems():
            value_and_op = self.filter_fields_op_dict[attr]
            _, op = value_and_op
            if attr in self.instance._indexed_fields:
                # 如果该字段可索引 改字段不能使用 in 操作
                if not self.indexed_field:
                    self.indexed_field = attr
                else:
                    raise FieldValidationError('Index field must only one')
            elif attr in self.instance._indexed_value_fields:
                # 如果该字段是索引值 可使用 in  操作
                if op in ['eq', 'in_']:
                    self.instance.filter_fields.append(attr)
                else:
                    raise FieldValidationError('%s: only support "=/in"' % attr)
            else:
                raise FieldValidationError('%s: not indexed value' % attr)
        return self.instance

    def order_by(self, arg):
        '''
        :param arg: Model.account.desc()
        :return: query
        fields = field + filter_fields
        1. 如果fields 只有一个值 那么 索引只用这一个
        例如: feed:date_created
        2. 如果fields 有大于1个值:
            * 如果有meta_field(索引+meta_field) 索引为meta+attr
            例如: feed:account_id:1000:date_created
            * 如果没有meta_field 判断是不是联合索引
            例如：feed:account_id:1000:action:update:date_created
        '''
        self.instance = self.model_class(**self.filter_fields_value_dict)
        # 验证索引是否正确 （只有一个排序索引，index_value 必须是 等 操作
        self._validate_filter_values()
        field_name, sorted = arg
        if field_name not in self.instance._indexed_fields:
            raise FieldValidationError('%s not indexed field' % field_name)
        self.sort_key = field_name
        fields = set([field_name])
        for attr in self.filter_fields_value_dict:
            fields.add(attr)
        fields_len = len(fields)
        meta_field = self.instance._indexed_meta_field
        if fields_len == 1:
            self.indexed_key = self.instance._indexed_key_for_attr(field_name)
        elif fields_len == 2 and meta_field in fields:
            self.indexed_key = self.instance._indexed_key_for_attr_with_meta(field_name)
        else:
            # 对比所有联合索引
            unique_attrs = self.instance._indexed_unique_fields
            for attrs in unique_attrs:
                if set(attrs) == fields:
                    self.indexed_key = self.instance._get_indexed_key_for_unique(attrs)
        if not self.indexed_key:
            raise FieldValidationError('%s not indexed field' % str(list(fields)))
        if sorted == 'desc':
            self.sort_dict['desc'] = True
        elif sorted == 'asc':
            self.sort_dict['desc'] = False
        query = copy.deepcopy(self)
        return query

    def offset(self, offset):
        self._offset = offset
        query = copy.deepcopy(self)
        return query

    def limit(self, limit):
        self._limit = limit
        query = copy.deepcopy(self)
        return query

    def _prepare_filter_values(self, filter_value, op, field_name):
        descriptor = self.instance.attributes[field_name]
        if isinstance(filter_value, tuple):
            rmax, rmin = filter_value
        else:
            filter_value = descriptor.typecast_for_storage(filter_value)
        if op == 'between':
            max = descriptor.typecast_for_storage(rmax)
            min = descriptor.typecast_for_storage(rmin)
        elif op == 'eq':
            min, max = filter_value, filter_value
        elif op == 'lt':
            min, max = '-inf', filter_value
        elif op == 'lte':
            min, max = '-inf', '(%s' % filter_value
        elif op == 'gt':
            min, max = filter_value, '+inf'
        elif op == 'gte':
            min, max = '(%s' % filter_value, '+inf'
        return max, min

    def _get_finall_index_key(self):
        redis_client = self.instance.__redis_client__
        with redis_client.pipeline(transaction=False) as p:
            for key in self.indexed_key:
                p.exists(self.indexed_key)
            is_exists = p.execute()
        with redis_client.pipeline(transaction=False) as p:
            for i, indexed_key in enumerate(self.indexed_key):
                if not is_exists[i]:
                    p.zunionstore(
                        indexed_key,
                        _get_recent_indexes(indexed_key, self.instance.__expire__),
                        aggregate='MAX')
                    p.expire(indexed_key, self.instance.__expire__)
            p.execute()
        if self.indexed_key and isinstance(self.indexed_key, (list, tuple)):
            if len(self.indexed_key) == 1:
                return self.indexed_key[0]
            else:
                indexes_key = sorted(list(self.indexed_key))
                indexed_key = hash(','.join(indexes_key))
                is_exists = redis_client.exists(indexed_key)
                if not is_exists:
                    redis_client.zunionstore(indexed_key, indexes_key,
                                             aggregate='MAX')
                    redis_client.expire(indexed_key, 60)
                return indexed_key
        else:
            return self.indexed_key

    def all(self):
        # 如果索引不存在，用最新的两个 key 合成，并设置过期时间
        if isinstance(self.indexed_key, list):
            indexed_key = self._get_finall_index_key()
        else:
            indexed_key = self.indexed_key
        with self.instance.__redis_client__.pipeline(transaction=False) as p:
            filter_value_and_op = self.filter_fields_op_dict.get(self.sort_key)
            if filter_value_and_op:
                filter_value, op = filter_value_and_op
            else:
                filter_value, op = None, None
            if not filter_value:
                start = self._offset
                end = self._limit + self._offset - 1
                if self.sort_dict.get('desc'):
                    p.zrevrange(indexed_key, start, end)
                else:
                    p.zrange(indexed_key, start, end)
            else:
                args = [indexed_key, 'max', 'min']
                kwargs = {'start': self._offset, 'num': self._limit}

                max_value, min_value = self._prepare_filter_values(
                    filter_value, op, self.sort_key)
                args[1], args[2] = max_value, min_value

                if self.sort_dict.get('desc'):
                    p.zrevrangebyscore(*args, **kwargs)
                else:
                    p.zrangebyscore(*args, **kwargs)

            values = p.execute()
            ids = values[0]

        results = self.model_class.batch_get_by_ids(ids)
        return results

    def count(self, start='-inf', end='+inf'):
        '''
        return indexed_key count
        '''
        redis_client = self.instance.__redis_client__
        indexed_key = self._get_finall_index_key()
        counts = redis_client.zcount(indexed_key, start, end)
        return counts
