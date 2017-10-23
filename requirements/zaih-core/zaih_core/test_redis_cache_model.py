# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import random
from datetime import datetime

import redis
from mockredis import mock_strict_redis_client
from zaih_core.redis_cache_fields import (
    DateTimeField, CharField, IntegerField,
    BooleanField, ListField, JsonField)
from zaih_core.ztime import now
from zaih_core.redis_cache_model import CacheModel
from zaih_core.ztime import date2timestamp

redis_client = mock_strict_redis_client()
# redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)


class RCNotice(CacheModel):

    __model_name__ = 'rcnotice'
    __redis_client__ = redis_client
    __expire__ = 86400 * 7 * 3
    __created_at__ = 'date_created'

    __index_meta__ = 'receiver_id'
    __unique_index__ = (
        ('category', 'date_created'),
        ('receiver_id', 'is_read', 'notice_id'),
        ('receiver_id', 'is_read', 'date_created'),
        ('receiver_id', 'category', 'date_created'),
        ('receiver_id', 'category', 'is_read', 'date_created'),
    )

    id = CharField('id', required=True)
    receiver_id = IntegerField('receiver_id', required=True, index_value=True)
    target_id = CharField('target_id', required=True)
    target_type = CharField('target_type', required=True)
    action = CharField('action', required=True)
    category = CharField('category', required=True, index_value=True)
    title = CharField('title', required=True)
    content = CharField('content', required=False)
    sender_ids = ListField('sender_ids', required=True, default=[])
    target_info = JsonField('target_info', required=False, default={})
    is_read = BooleanField('is_read', required=True, index_value=True,
                           default=False)
    notice_id = IntegerField('notice_id', required=True, indexed=True)
    date_created = DateTimeField('date_created', required=True, indexed=True)

    @property
    def _created_at(self):
        return date2timestamp(self.date_created)


def test_query():
    params = dict(receiver_id=2,
                  target_id='10',
                  target_type='question',
                  action='ask',
                  category='ask',
                  title='向你提了问题',
                  content='你说这个cache 好用么',
                  sender_ids=[2],
                  date_created=now())
    for i in range(10):
        params['id'] = str(i)
        params['reveiver_id'] = i
        params['notice_id'] = i
        params['action'] == random.choice(['ask', 'quesiton'])
        cn = RCNotice(**params)
        cn.save()

    query = (RCNotice.query()
             .filter(RCNotice.receiver_id.eq(2))
             # .filter(RCNotice.receiver_id.in_([2, 4]))
             .filter(RCNotice.notice_id.eq(2))
             .filter(RCNotice.is_read.eq(False))
             .order_by(RCNotice.notice_id.desc()))
    results = query.offset(0).limit(2).all()
    assert len(results) == 1
    assert results[0].id == '2'

    query = (RCNotice.query()
             .filter(RCNotice.receiver_id.in_([2, 4]))
             .filter(RCNotice.notice_id.eq(2))
             .filter(RCNotice.is_read.eq(False))
             .order_by(RCNotice.notice_id.desc()))
    results = query.offset(0).limit(2).all()
    assert len(results) == 1
    assert results[0].id == '2'

    query = (
        RCNotice.query()
        .filter(RCNotice.category.eq('ask'))
        .order_by(RCNotice.date_created.desc()))
    results = query.limit(1).all()
    assert len(results) == 1
    assert results[0].id == '9'


def test_curd():
    # test curd
    cn = RCNotice(id='6',
                  receiver_id=2,
                  target_id='10',
                  target_type='question',
                  action='ask',
                  category='ask',
                  title='向你提了问题',
                  content='你说这个cache 好用么',
                  sender_ids=[2],
                  notice_id=100,
                  date_created=datetime(2017, 9, 11))
    cn.save()
    assert cn.id == '6'
    cn = RCNotice.get_by_id(6)
    assert cn.id == '6'
    assert cn.receiver_id == 2
    cn = cn.update(title='test update')
    assert cn.title == 'test update'
    cns = RCNotice.batch_get_by_ids([6])
    assert len(cns) == 1
    assert cns[0].id == '6'
    cn = RCNotice.get_by_id(6)
    cn.delete()
    cn = RCNotice.get_by_id(6)
    assert cn is None


def main():
    test_curd()
    test_query()


if __name__ == '__main__':
    main()
