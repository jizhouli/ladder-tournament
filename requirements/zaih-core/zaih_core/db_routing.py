# -*- coding: utf-8 -*-

import logging
from functools import wraps
from functools import partial

import sqlalchemy.orm as orm
from sqlalchemy.orm import scoped_session, sessionmaker
from flask.ext.sqlalchemy import SQLAlchemy as SQLAlchemyBase, get_state

log = logging.getLogger(__name__)


class AutoRouteSession(orm.Session):

    def __init__(self, db, autocommit=False, autoflush=False, **options):
        self.db = db
        self.app = db.get_app()
        self._model_changes = {}
        orm.Session.__init__(
            self,
            autocommit=autocommit,
            autoflush=autoflush,
            bind=db.engine,
            binds=db.get_binds(self.app),
            **options)

    def get_bind(self, mapper=None, clause=None):
        try:
            state = get_state(self.app)
        except (AssertionError, AttributeError, TypeError) as err:
            log.info("Unable to get Flask-SQLAlchemy configuration. Outputting default bind. Error:" + err)
            return orm.Session.get_bind(self, mapper, clause)

        # If there are no binds configured, connect using the default SQLALCHEMY_DATABASE_URI
        if state is None or not self.app.config['SQLALCHEMY_BINDS']:
            if not self.app.debug:
                log.debug("Connecting -> DEFAULT. Unable to get Flask-SQLAlchemy bind configuration. Outputting default bind.")
            return orm.Session.get_bind(self, mapper, clause)
        # Writes go to the master
        elif self._flushing:  # we who are about to write, salute you
            log.debug("Connecting -> MASTER")
            return state.db.get_engine(self.app, bind='master')
        # Everything else goes to the slave
        else:
            log.debug("Connecting -> SLAVE")
            return state.db.get_engine(self.app, bind='slave')

    def using_bind(self, name):
        s = AutoRouteSession(self.db)
        vars(s).update(vars(self))
        s._name = name
        return s


class AutoRouteSQLAlchemy(SQLAlchemyBase):

    def __init__(self, *args, **kwargs):
        SQLAlchemyBase.__init__(self, *args, **kwargs)
        self.session.using_bind = lambda s: self.session().using_bind(s)

    def create_scoped_session(self, options=None):
        """Helper factory method that creates a scoped session."""
        if options is None:
            options = {}
        scopefunc = options.pop('scopefunc', None)
        return orm.scoped_session(
            partial(AutoRouteSession, self, **options), scopefunc=scopefunc
        )

slave = AutoRouteSQLAlchemy(session_options={'autocommit': True})


def get_session():
    from zaih_core.database import db
    master_engine = db.engine
    Session = scoped_session(sessionmaker(bind=master_engine))
    return Session


def with_slave(fn):

    @wraps(fn)
    def go(*arg, **kw):
        slave_engine = slave.engine
        s = get_session()
        oldbind = s.bind
        s.bind = slave_engine
        try:
            return fn(*arg, **kw)
        finally:
            s.bind = oldbind
    return go
