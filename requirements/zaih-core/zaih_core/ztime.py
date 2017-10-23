# -*- coding: utf-8 -*-
# 时间处理相关方法

import pytz
from datetime import datetime, timedelta, date, time

bjtz = pytz.timezone('Asia/Shanghai')


ONE_MINUTE = 60
TWO_MINUTE = 60 * 2
ONE_HOUR = 60 * 60
ONE_DAY = 24 * 60 * 60


# http://stackoverflow.com/questions/24856643/unexpected-results-converting-timezones-in-python
def str_time(dt, fmt='%Y-%m-%d %H:%M:%S', with_timezone=False):
    """将数据库取出来的时间转化为北京时间字符串"""
    if not dt or not isinstance(dt, (datetime, date, time)):
        # 取出来的值为空或者不是日期类型，直接返回
        return dt
    if not dt.tzinfo:
        # 没有时间戳信息，加上utc
        dt = pytz.utc.localize(dt)
    bjdt = dt.astimezone(bjtz)

    if with_timezone:
        fmt = "%Y-%m-%d %H:%M:%S %Z%z"
    str_time = bjdt.strftime(fmt)
    return str_time


def str_to_time(dt_str):
    """将时间字符串转化为带有时间戳的datetime类型"""
    formats = ['%Y-%m-%d %H:%M', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S']
    for format in formats:
        try:
            dt = datetime.strptime(dt_str, format)
            # 默认认为时间字符串所表示的是北京时间
            bjdt = bjtz.localize(dt)
            utcdt = bjdt.astimezone(pytz.utc)
            return utcdt
        except:
            pass
    return


def date2timestamp(dt):
    # datetime to timestamp
    import time
    if not isinstance(dt, datetime):
        return datetime
    timestamp = time.mktime(dt.timetuple()) + dt.microsecond/1e6
    return timestamp


def timestamp2date(timestamp):
    if not isinstance(timestamp, (int, float)):
        return timestamp
    date = datetime.utcfromtimestamp(timestamp)
    utcdt = pytz.utc.localize(date)
    return utcdt


def now(tz='utc'):
    """返回带有时间戳的当前时间，默认为utc时间"""
    if tz == 'beijing':
        return datetime.now(bjtz)
    return datetime.now(pytz.utc)
# now的实际意义
now_with_tz = now


def today_begin_with_tz():
    """获取北京当前时间下一天的开始时间"""
    today_begin = datetime.combine(now(tz='beijing').date(), datetime.min.time())
    return bjtz.localize(today_begin)


def start_end_this_week():
    """返回当前所在周的开始时间和结束时间"""
    tb = today_begin_with_tz()
    start = tb - timedelta(days=tb.weekday())
    end = start + timedelta(days=7)
    return start, end


def time_since(dt, default=u'刚刚', fmt='%Y-%m-%d %H:%M', suffix=None):
    """根据datetime返回特定字符串"""
    if not (dt and isinstance(dt, datetime)):
        return ''
    if not dt.tzinfo:
        # 没有时间戳信息，默认为utc
        dt = pytz.utc.localize(dt)
    # 北京时间
    result = default
    dt = dt.astimezone(bjtz)
    now = datetime.now(bjtz)
    diff = now - dt
    total_seconds = int(diff.total_seconds())
    if total_seconds >= 120:
        # 大于等于2min
        if total_seconds < 3600 * 24 * 3:
            # 24 小时内
            periods = (
                (total_seconds / (3600 * 24), u'天'),
                (total_seconds / 3600, u'小时'),
                (total_seconds / 60, u'分钟'),
            )
            for period, unit in periods:
                if period > 0:
                    result = u'%d%s前' % (period, unit)
                    break
        else:
            # 72 小时后显示时间
            result = unicode(dt.strftime(fmt))
    if suffix:
        result = u'%s%s' % (result, suffix)
    return result


def weekday_to_zh(weekday):
    if not isinstance(weekday, int) or weekday < 0 or weekday > 6:
        return weekday
    days_zh = [u'周一', u'周二', u'周三', u'周四', u'周五', u'周六', u'周日']
    return days_zh[weekday]


def format_time(dt, format='%m月%d日 %H:%M'):
    '''datetime格式化成字符串'''
    if not (dt and isinstance(dt, datetime)):
        return ''
    if not dt.tzinfo:
        # 没有时间戳信息，默认为utc
        dt = pytz.utc.localize(dt)
    dt = dt.astimezone(bjtz)
    return unicode(dt.strftime(format), 'utf-8')


def format_utc_str_to_datetime(utc_str):
    """2017-01-05T10:49:13.135202+00:00"""
    import dateutil.parser
    if not (utc_str and isinstance(utc_str, (str, unicode))):
        return datetime
    return dateutil.parser.parse(utc_str)


def count_down(
        dt, hour=24, only_seconds=False,
        format='{hours:02d}:{minutes:02d}:{seconds:02d}'):
    utcnow = now().replace(tzinfo=None)
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    dt = dt.astimezone(pytz.utc)
    dt = dt.replace(tzinfo=None)
    total_seconds = int((utcnow - dt).total_seconds())
    left_seconds = max(0, hour * 3600 - total_seconds)
    if only_seconds:
        return left_seconds
    left_hours = max(0, left_seconds // 3600)
    left_minutes = max(0, (left_seconds % 3600) // 60)
    seconds = max(0, (left_seconds % 3600) % 60)
    res = format.format(
        hours=left_hours, minutes=left_minutes, seconds=seconds)
    return res


def format_datetime_to_zh(_time):
    if not isinstance(_time, datetime):
        return ""
    current_time = now('beijing')
    _time = _time.astimezone(bjtz)
    if current_time > _time:
        # 过去的时间
        diff = int(round((current_time - _time).total_seconds()))
        if diff < TWO_MINUTE:
            return "刚刚"
        elif diff < ONE_HOUR:
            return "%s分钟前" % (diff / ONE_MINUTE)
        elif current_time.date() == _time.date() and diff < ONE_DAY:
            return "%s小时前" % (diff / ONE_HOUR)
        elif (current_time.date() - _time.date()).days == 1:
            return "昨天"
        elif current_time.year == _time.year:
            return "%02d-%02d" % (_time.month, _time.day)
        else:
            return "%02d-%02d-%02d" % (_time.year, _time.month, _time.day)
    elif current_time < _time:
        # 未来的时间
        diff = int(round((_time - current_time).total_seconds()))
        if diff < TWO_MINUTE:
            return "马上"
        elif diff < ONE_HOUR:
            return "%s分钟后" % (diff / ONE_MINUTE)
        elif current_time.date() == _time.date() and diff < ONE_DAY:
            return "%s小时后" % (diff / ONE_HOUR)
        elif (_time.date() - current_time.date()).days == 1:
            return "明天"
        elif current_time.year == _time.year:
            return "%02d-%02d" % (_time.month, _time.day)
        else:
            return "%02d-%02d-%02d" % (_time.year, _time.month, _time.day)


if __name__ == '__main__':
    print start_end_this_week()
