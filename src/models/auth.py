# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
from datetime import timedelta, datetime
from sqlalchemy import sql
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from zaih_core.database import (Model, SurrogatePK, DateTime, db,
                                JsonString)

__all__ = [
    'WXAuthentication',
    'OAuth2Token',
]


class WXAuthentication(SurrogatePK, Model):

    OPENID_TYPE_XCX = 'XiaoChengXu'
    OPENID_TYPE_GZH = 'GongZhongHao'
    OPENID_TYPE_APP = 'APP'

    CLIENT_LT = 'LadderTournament'

    __tablename__ = 'wx_authentication'
    __table_args__ = (
        db.UniqueConstraint('account_id', 'client', 'openid_type'),
    )

    unionid = db.Column(db.String(64), nullable=True)
    openid = db.Column(db.String(64), nullable=False)
    openid_type = db.Column(db.String(64), nullable=False)
    client = db.Column(db.String(64), nullable=False,
                       server_default=CLIENT_LT)

    account_id = db.Column(db.Integer(), nullable=False, index=True)
    date_updated = db.Column(DateTime,
                             nullable=False, index=True,
                             server_default=db.func.current_timestamp(),
                             onupdate=db.func.current_timestamp())

    account = db.relationship(
        'Account',
        primaryjoin='WXAuthentication.account_id==Account.id',
        foreign_keys='WXAuthentication.account_id')


class OAuth2Token(Model):

    __tablename__ = 'oauth2_token'

    EXPIRE_DAY = 7

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(40), nullable=False)
    account_id = db.Column(db.Integer, index=True)
    token_type = db.Column(db.String(40))
    session_key = db.Column(db.String(40), nullable=True)
    access_token = db.Column(db.String(255), unique=True)
    refresh_token = db.Column(db.String(255), unique=True)
    expires = db.Column(db.DateTime)
    scopes = db.Column(JsonString(1024))

    account = db.relationship(
        'Account',
        primaryjoin='OAuth2Token.account_id==Account.id',
        foreign_keys='OAuth2Token.account_id')

    @hybrid_property
    def expires_timestamp(self):
        import time
        et = time.mktime(self.expires.utctimetuple())
        return et

    @hybrid_property
    def expires_in(self):
        try:
            expires_in = int((self.expires - datetime.utcnow()).total_seconds())
        except:
            expires_in = 0
        return expires_in

    @expires_in.setter
    def set_expires_in(self, expires_in):
        self.expires = datetime.utcnow() + timedelta(seconds=expires_in)

    def is_expired(self):
        return self.expires < datetime.utcnow()

    def is_refresh_token_expired(self):
        return self.expires + timedelta(days=self.EXPIRE_DAY) < datetime.utcnow()

    @classmethod
    def get_token_info(cls, token, is_refresh_token=False):
        if is_refresh_token:
            token = cls.query.filter_by(refresh_token=token).first()
            if token.is_refresh_token_expired():
                token = cls.get_or_create(token.client_id,
                                          token.account_id, token.token_type)
                return token.as_dict()
            return None
        else:
            token = cls.query.filter_by(access_token=token).first()
            if not token or token.is_expired():
                return None
            return token.as_dict()

    @classmethod
    def get_or_create(cls, client_id, account_id, session_key=None,
                      token_type='Bearer'):
        # get or create valid access token
        token = None
        if not token or token.is_expired():
            from oauthlib.common import generate_token
            token = cls.create(client_id=client_id,
                               account_id=account_id,
                               token_type=token_type,
                               session_key=session_key,
                               expires_in=3600*24*cls.EXPIRE_DAY,
                               access_token=generate_token(),
                               refresh_token=generate_token(),
                               scopes=["open"])
        return token

    def as_dict(self):
        return {
            'client_id': self.client_id,
            'account_id': self.account_id,
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'session_key': self.session_key,
            'expires_timestamp': self.expires_timestamp,
            'scopes': self.scopes,
        }
