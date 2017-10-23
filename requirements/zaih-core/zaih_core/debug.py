# -*- coding:utf-8 -*-

from __future__ import unicode_literals

import time
import cProfile
import StringIO
import pstats

from flask import current_app as app
from functools import wraps


def timeit(fn):

    @wraps(fn)
    def real_fn(*args, **kwargs):

        _start = time.time()
        result = fn(*args, **kwargs)
        _end = time.time()
        _last = _end - _start
        app.logger.debug('End timeit for %s in %s seconds.' %
                         (fn.__name__, _last))
        return result

    return real_fn


def cprofile(fn):
    '''
    用cProfile输出时间统计信息
    '''

    @wraps(fn)
    def _fn(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()
        result = fn(*args, **kwargs)
        pr.disable()
        s = StringIO.StringIO()
        sortby = 'cumulative'
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        app.logger.debug(s.getvalue())
        return result
    return _fn


try:
    from line_profiler import LineProfiler
except:
    class LineProfiler():

        def __call__(self, func):
            return func

        def print_stats(self):
            pass

ln_profile = LineProfiler()


def lprofile(fn):
    '''
    用line_profiler输出代码行时间统计信息
    '''
    fn = ln_profile(fn)

    @wraps(fn)
    def _fn(*args, **kwargs):
        result = fn(*args, **kwargs)
        app.logger.debug(ln_profile.print_stats())
        return result
    return _fn


try:
    from memory_profiler import LineProfiler, show_results

    def mm_profile(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            prof = LineProfiler()
            val = prof(func)(*args, **kwargs)
            show_results(prof)
            return val
        return wrapper
except:
    mm_profile = lambda x: x


def mprofile(fn):
    '''
    用memory_profiler输出代码行内存统计信息
    '''
    _fn = mm_profile(fn)
    return _fn
