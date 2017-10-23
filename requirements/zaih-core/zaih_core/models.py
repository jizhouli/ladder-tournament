# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six


class ApiModel(object):

    @classmethod
    def object_from_dictionary(cls, entry):
        # make dict keys all strings
        if entry is None:
            return ""
        entry_str_dict = dict([(str(key), value)
                               for key, value in entry.items()])
        return cls(**entry_str_dict)

    def __repr__(self):
        return str(self)
        # if six.PY2:
        #     return six.text_type(self).encode('utf8')
        # else:
        #     return self.encode('utf8')

    def __str__(self):
        if six.PY3:
            return self.__unicode__()
        else:
            return unicode(self).encode('utf-8')


class User(ApiModel):
    def __init__(self, id, *args, **kwargs):
        self.id = id
        for key, value in six.iteritems(kwargs):
            setattr(self, key, value)

    def __unicode__(self):
        return "User: %s" % self.realname
