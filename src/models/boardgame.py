# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from sqlalchemy import sql

import time

from flask import g
from flask.ext.login import UserMixin

from zaih_core.database import (Model, SurrogatePK, DateTime, db)
from zaih_core.caching import cache_for


__all__ = [
	'Shop',
	'Table',
	'Tournament',
	'Round',
]


class Location(Base):

    __tablename__ = 'locations'

    id = Column(Integer, primary_key=True)
    desc = Column(String(256), nullable=True)
    lon = Column(Float)
    lat = Column(Float)


class Shop(SurrogatePK, Model):

	__tablename__ = 'shops'

	name = db.Column(db.String(64), nullable=True)

	# location infomations
	province = db.Column(db.String(32), nullable=True)
	city = db.Column(db.String(32), nullable=True)
	county = db.Column(db.String(32), nullable=True)
	address = db.Column(db.String(256), nullable=True)
	location_id = db.Column(db.Integer(), nullable=True)


class Table(SurrogatePK, Model):

	__tablename__ = 'tables'

	shop_id = db.Column(db.Integer(), nullable=False, index=True)

	shop = db.relationship(
		'Shop',
		primaryjoin='Table.shop_id==Shop.id',
        foreign_keys='Table.shop_id')


class Tournament(SurrogatePK, Model):

	__tablename__ = 'tournaments'

	table_id = db.Column(db.Integer(), nullable=False, index=True)

	table = db.relationship(
		'Table',
		primaryjoin='Tournament.table_id==Table.id',
        foreign_keys='Tournament.table_id')


class Round(SurrogatePK, Model):

	__tablename__ = 'rounds'

	tournament_id = db.Column(db.Integer(), nullable=False, index=True)

	tournament = db.relationship(
		'Tournament',
		primaryjoin='Round.tournament_id==Tournament.id',
        foreign_keys='Round.tournament_id')








