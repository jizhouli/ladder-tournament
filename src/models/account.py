# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from sqlalchemy import sql

import time
from flask import g
from flask.ext.login import UserMixin

from zaih_core.database import (Model, SurrogatePK, DateTime, db)
from zaih_core.caching import cache_for


__all__ = [
    'Account',
]


class Account(SurrogatePK, UserMixin, Model):
    __tablename__ = 'account'

    # select setval('account_id_seq', 10000001, false);

    unikey = db.Column(db.String(256), nullable=True, unique=True, index=True)
    nickname = db.Column(db.String(64), nullable=True)
    realname = db.Column(db.String(64), nullable=True)
    _avatar = db.Column(db.String(256), nullable=True)
    title = db.Column(db.String(), nullable=True)
    is_verified = db.Column(db.Boolean(), nullable=False, index=True,
                            server_default=sql.false())
    date_updated = db.Column(DateTime,
                             index=True, nullable=False,
                             server_default=db.func.current_timestamp())

    @property
    def avatar(self):
        return self._avatar

    @property
    def wxapp_openid(self):
        from src.models.auth import WXAuthentication

        auth = (WXAuthentication.query
                .filter_by(account_id=self.id,
                           openid_type=WXAuthentication.OPENID_TYPE_XCX)
                .first())
        if auth:
            return auth.openid
        return ""
