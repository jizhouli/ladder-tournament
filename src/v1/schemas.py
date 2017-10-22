# -*- coding: utf-8 -*-

# TODO: datetime support

###
### DO NOT CHANGE THIS FILE
### 
### The code is auto generated, your change will be overwritten by 
### code generating.
###


DefinitionsId = {'type': 'integer', 'format': 'int32'}
DefinitionsHello = {'type': 'string'}
DefinitionsAccount_id = {'type': 'integer', 'format': 'int32'}
DefinitionsSuccess = {'properties': {'ok': {'type': 'boolean'}}}
DefinitionsAccount = {'required': ['account_id'], 'description': u'\u8fd4\u56de\u7684\u7528\u6237\u4fe1\u606f', 'properties': {'account_id': {'type': 'integer', 'format': 'int32'}}}
DefinitionsDatetime = {'type': 'string', 'format': 'datetime'}
DefinitionsNone = {'type': 'object'}
DefinitionsWxuserinfowithcode = {'properties': {'raw_data': {'type': 'string'}, 'code': {'type': 'string'}, 'iv': {'type': 'string'}, 'encrypted_data': {'type': 'string'}, 'signature': {'type': 'string'}}}
DefinitionsTokendetail = {'properties': {'token_type': {'default': 'Bearer', 'type': 'string'}, 'scopes': {'items': {'type': 'string', 'description': u'token \u7c7b\u578b'}, 'type': 'array'}, 'account_id': {'type': 'integer', 'format': 'int32'}, 'is_new_weixin_app': {'type': 'boolean'}, 'access_token': {'type': 'string'}, 'expires_in': {'type': 'integer', 'format': 'int32'}, 'refresh_token': {'type': 'string'}}}
DefinitionsError = {'properties': {'text': {'type': 'string'}, 'message': {'type': 'string'}, 'error_code': {'type': 'string'}}}

validators = {
    ('code_token', 'POST'): {'headers': {'required': ['Authorization'], 'properties': {'Authorization': {'type': 'string'}}}, 'json': DefinitionsWxuserinfowithcode},
}

filters = {
    ('code_token', 'POST'): {200: {'headers': None, 'schema': DefinitionsTokendetail}},
    ('hello', 'GET'): {200: {'headers': None, 'schema': DefinitionsHello}},
}

scopes = {
    ('code_token', 'POST'): ['open'],
    ('hello', 'GET'): ['open'],
}


class Security(object):

    def __init__(self):
        super(Security, self).__init__()
        self._loader = lambda: []

    @property
    def scopes(self):
        return self._loader()

    def scopes_loader(self, func):
        self._loader = func
        return func

security = Security()


def merge_default(schema, value, get_first=True):
    # TODO: more types support
    type_defaults = {
        'integer': 9573,
        'string': 'something',
        'object': {},
        'array': [],
        'boolean': False
    }

    results = normalize(schema, value, type_defaults)
    if get_first:
        return results[0]
    return results


def normalize(schema, data, required_defaults=None):

    import six

    if required_defaults is None:
        required_defaults = {}
    errors = []

    class DataWrapper(object):

        def __init__(self, data):
            super(DataWrapper, self).__init__()
            self.data = data

        def get(self, key, default=None):
            if isinstance(self.data, dict):
                return self.data.get(key, default)
            return getattr(self.data, key, default)

        def has(self, key):
            if isinstance(self.data, dict):
                return key in self.data
            return hasattr(self.data, key)

        def keys(self):
            if isinstance(self.data, dict):
                return list(self.data.keys())
            return list(vars(self.data).keys())

        def get_check(self, key, default=None):
            if isinstance(self.data, dict):
                value = self.data.get(key, default)
                has_key = key in self.data
            else:
                try:
                    value = getattr(self.data, key)
                except AttributeError:
                    value = default
                    has_key = False
                else:
                    has_key = True
            return value, has_key

    def _normalize_dict(schema, data):
        result = {}
        if not isinstance(data, DataWrapper):
            data = DataWrapper(data)

        for key, _schema in six.iteritems(schema.get('properties', {})):
            # set default
            type_ = _schema.get('type', 'object')

            # get value
            value, has_key = data.get_check(key)
            if has_key:
                result[key] = _normalize(_schema, value)
            elif 'default' in _schema:
                result[key] = _schema['default']
            elif key in schema.get('required', []):
                if type_ in required_defaults:
                    result[key] = required_defaults[type_]
                else:
                    errors.append(dict(name='property_missing',
                                       message='`%s` is required' % key))

        for _schema in schema.get('allOf', []):
            rs_component = _normalize(_schema, data)
            rs_component.update(result)
            result = rs_component

        additional_properties_schema = schema.get('additionalProperties', False)
        if additional_properties_schema:
            aproperties_set = set(data.keys()) - set(result.keys())
            for pro in aproperties_set:
                result[pro] = _normalize(additional_properties_schema, data.get(pro))

        return result

    def _normalize_list(schema, data):
        result = []
        if hasattr(data, '__iter__') and not isinstance(data, dict):
            for item in data:
                result.append(_normalize(schema.get('items'), item))
        elif 'default' in schema:
            result = schema['default']
        return result

    def _normalize_default(schema, data):
        if data is None:
            return schema.get('default')
        else:
            return data

    def _normalize(schema, data):
        if not schema:
            return None
        funcs = {
            'object': _normalize_dict,
            'array': _normalize_list,
            'default': _normalize_default,
        }
        type_ = schema.get('type', 'object')
        if not type_ in funcs:
            type_ = 'default'

        return funcs[type_](schema, data)

    return _normalize(schema, data), errors

