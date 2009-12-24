# -*- coding: utf-8 -*-

"""
Author    : shaovie@gmail.com
Summary   : ...
"""

from heapq import heappush, heappop, heapify
from datetime import datetime, timedelta
from time import time
from bisect import bisect
import calendar
import re
from pyndk.event_handler import EventHandler, TIMER_MASK
from collections import deque

_PRE_ALLOC_TIMER_ID_COUNT = 32

MONTH_LIST = ["jan", "feb", "mar", "apr", "may", "jun",
              "jul", "aug", "sep", "oct", "nov", "dec"]
WDAY_LIST  = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]

# For crontab
FIRST_MINUTE  = 0
LAST_MINUTE   = 59
MINUTE_COUNT  = 60

FIRST_HOUR    = 0
LAST_HOUR     = 23
HOUR_COUNT    = 24

FIRST_MDAY    = 1
LAST_MDAY     = 31
MDAY_COUNT    = 32

FIRST_MONTH   = 1
LAST_MONTH    = 12
MONTH_COUNT   = 13

FIRST_WDAY    = 0
LAST_WDAY     = 7
WDAY_COUNT    = 8

GENERAL_TIMER = 0x11
CRONTAB_TIMER = 0x12

RE_CHECK_ENTRY = re.compile(r'[a-z]+')

class TimerNode(object):
    """
    """
    def __init__(self, timerid, ehandler, arg, tv, inter):
        self.timer_id  = timerid
        self.ehandler  = ehandler
        self.arg       =  arg
        self.timer_value = tv 
        self.interval  = inter
        self.cron_entrys = {\
                        'min': [], 
                       'hour': [], 
                       'mday': [], 
                      'month': [], 
                       'wday': [],
                       }

    def __eq__(self, obj):
        return self.timer_value == obj.timer_value

    def __ge__(self, obj):
        return self.timer_value >= obj.timer_value

    def __gt__(self, obj):
        return self.timer_value > obj.timer_value

    def __le__(self, obj):
        return self.timer_value <= obj.timer_value

    def __lt__(self, obj):
        return self.timer_value < obj.timer_value

    def __ne__(self, obj):
        return self.timer_value != obj.timer_value

class TimerQueue(EventHandler):
    """
    """
    def __init__(self, reactor):
        EventHandler.__init__(self)
        self._timer_queue = []
        self._crontab_queue = []
        self._timer_ids = deque()
        self._timer_id_index = 0
        self._cur_size  = 0
        self.set_reactor(reactor)

    def empty(self):
        """
        Return timer queue is empty or not.
        """
        return not self._cur_size

    def schedule(self, ehandler, arg, delay_time, interval_time):
        """
        Schedule a timer. 
        Return a timer id (non-negative integeron successfully, return -1 on
        failed.
        """
        if not ehandler: return -1
        #if not hasattr(ehandler, 'handle_close') and not callable(ehandler):
        #    return -1

        if delay_time <= 0.005:
            tv = time()
        else:
            tv = time() + delay_time
        timerid = self._pop_timer_id()

        node = TimerNode(timerid, ehandler, arg, tv, interval_time)
        heappush(self._timer_queue, node)
        self._cur_size += 1
        return timerid

    def crontab(self, ehandler, arg, entry):
        """
        Format:
        *       *       *       *       *
        Min    Hour    Mday    Month   Wday

        The fields are:
        Min       minute of execution, 0-59
        Hour      hour of execution, 0-23
        Mday      day of month of execution, 1-31
        Month     month of execution, 1-12 (or names)
        Wday      day of week of execution, 0-7 (1 = monday, 0 or 7 = sunday, 
                  or names)

        Possible values:
        *       matches all values, e.g. a * in month means: "every month"
        x-y     matches the range x to y, e.g. 2-4 in Mday means "on the 
                2nd, 3rd, and 4th of the month"
        x/n     in range x with frequency n, e.g. */2 in Hour means "every other hour"

        Months can be names: jan, Feb, mAr (case insensitive). (use 3 chars)
        Weekdays can be names, e.g. sun, Mon, tUe. (use 3 chars, no case)

        Notes:
        1). Ranges and lists can be mixed. 
            e.g. 1,3-5 (means "1 3 4 5") 1,3-7/2 (means "1 3 5 7")
        2). Ranges can specify 'step' values. '10-16/2' is like '10,12,14,16'
        3). Ranges can be opened region. e.g. '2-' in hour means '2-23',
            '-15' in hour means '0-15', '-' is '*'
        4). List support '1,2,3,5-9,15-21/2,25/2,50-8,*/2,*,,' (this can be one entry,
            means '*', will calculate the collection of region.)

        Special entries:
        ------          -------
        @yearly         Run once a year, "0 0 1 1 *".
        @monthly        Run once a month, "0 0 1 * *".
        @weekly         Run once a week, "0 0 * * 0".
        @daily          Run once a day, "0 0 * * *".
        @hourly         Run once an hour, "0 * * * *".

        Examples:
        '30 0 1 1,6,12 *'       00:30 Hrs on 1st of Jan, June & Dec.
        '* * 1,15 * Sun'        Will run on the first and fifteenth AND every Sunday;
        '* 20 * 10 1-5'         8.00 PM every weekday (Mon-Fri) only in Oct.
        '0 7-23/3 * * *'        Every 3-hours while awake
        '*/5 6-13 * * mon-fri'  Every 5 minutes during market hours
        '0 12 * * 0,2,4'        Will run at noon every sun,tues,thurs 
        '0 18-7 * * 1-5'        6pm-7am every hour during weekdays.

        """
        # veritify
        if not ehandler: return -1
        #if not hasattr(ehandler, 'handle_close') and not callable(ehandler):
            #return -1
        if len(entry) < 6: return -1

        # convert string to number.
        entry_ = entry.lower()
        for i, m in enumerate(MONTH_LIST):
            entry_ = entry_.replace(m, str(i+1))
        for i, m in enumerate(WDAY_LIST):
            entry_ = entry_.replace(m, str(i))
        invalid_letter = RE_CHECK_ENTRY.search(entry_)
        if invalid_letter:
            raise (ValueError, "invalid letters '%s' in '%s'" \
                    % (",".join(invalid_letter.group()), entry))

        node = TimerNode(-1, ehandler, arg, None, None)

        # parse entry
        self._parse_crontab(entry_, node.cron_entrys)

        # calculate the future absolute time.
        timerid = self._pop_timer_id()

        #for k, v in node.cron_entrys.items():
        #    print("key = %s val = %s" % (k, v))
        node.timer_value = None
        node.timer_id = timerid

        # 
        if len(self._crontab_queue) == 0:
            if self.get_reactor().schedule_timer(self, None, 60, 60) == -1:
                self._push_timer_id(timerid)
                return False
        # push to timer queue.
        self._crontab_queue.append(node)
        self._cur_size += 1
        return timerid

    def expire(self, current_time = None):
        result = 0
        if not self._cur_size: return 0
        if not current_time: current_time = time()

        while self._cur_size > 0:
            node = self._dispatch_timer(current_time)
            if not node: break
            if hasattr(node.ehandler, 'handle_timeout'):
                ret = node.ehandler.handle_timeout(current_time, node.arg)
            else: 
                node.ehandler(current_time, node.arg)
            if not ret:
                if node.interval > 0.0:
                    self.cancel(node.timer_id, False)
                else:
                    node.ehandler.handle_close(node.arg, TIMER_MASK)
            result += 1
        return result


    def cancel(self, timer_id, dont_call_handle_close = True):
        """
        Cancel a timer by timerid.
        If <dont_call_handle_close> is False then the event-handler's
        'handle_close' will be called.
        """
        if timer_id < 0 or self._cur_size == 0:
            return False

        find = False
        index = 0
        for i, q in enumerate((self._timer_queue, self._crontab_queue)):
            for index, node in enumerate(q):
                if node and timer_id == node.timer_id:
                    find = True
                    if not dont_call_handle_close:
                        if hasattr(node.ehandler, 'handle_close'):
                            node.ehandler.handle_close(node.arg, TIMER_MASK)
                    break

            if find: 
                self._push_timer_id(timer_id)
                self._cur_size -= 1
                node = q.pop(index)
                node.in_used = False
                heapify(q)
                return True
        return False

    def get_timerid_by_handler(self, ehandler):
        """
        Get the timerid by ehandler.
        """
        if not ehandler: return -1

        for q in (self._timer_queue, self._crontab_queue):
            for node in q:
                if node and ehandler == node.ehandler:
                    return node.timer_id
        return -1

    def reset_interval(self, timer_id, interval_time):
        """
        Resets the interval of the timer represented by <timer_id> to
        <interval>.
        """
        if timer_id < 0 or self._cur_size == 0:
            return False

        find = False
        index = 0
        # If <reset_interval> be called in <handle_timeout>, 
        # timerid will be not found.
        for index, node in enumerate(self._timer_queue):
            if node and timer_id == node.timer_id:
                find = True
                break

        if not find: return False

        self._timer_queue[index].interval = interval_time
        self._timer_queue[index].timer_value = time() + interval_time
        heapify(self._timer_queue)
        return True

    def calculate_timeout(self, max_wait_time):
        """
        Determine the next event to timeout.
        """
        if not self._cur_size: return max_wait_time

        now = time()
        if self._timer_queue[0].timer_value > now:
            timeout = self._timer_queue[0].timer_value - now
            if max_wait_time == -1 or max_wait_time > timeout:
                return timeout
            return max_wait_time
        return 0

    def handle_timeout(self, curr_time, arg = None):
        """
        Implementation for crontab.
        """
        del_timers = []
        curr_time = datetime.fromtimestamp(curr_time)
        for idx, node in enumerate(self._crontab_queue):
            if curr_time.minute in node.cron_entrys['min']              \
                    and curr_time.hour in node.cron_entrys['hour']      \
                    and curr_time.month in node.cron_entrys['month']    \
                    and (curr_time.day in node.cron_entrys['mday'] or   \
                    curr_time.isoweekday() in node.cron_entrys['wday']):
                if hasattr(node.ehandler, 'handle_timeout'): 
                    ret = node.ehandler.handle_timeout(curr_time, node.arg)
                    if not ret: 
                        node.ehandler.handle_close(node.arg, TIMER_MASK)
                        self._cur_size -= 1
                        self._push_timer_id(node.timer_id)
                        del_timers.append(idx)
                else:
                    node.ehandler(current_time, node.arg)
        for id in del_timers:
            self._crontab_queue.pop(id)
        return len(self._crontab_queue) != 0

    ## Inner method
    #
    def _dispatch_timer(self, current_time):
        if (self._timer_queue[0].timer_value - current_time) <= 0.005:
            node = self._timer_queue.pop(0)
            if not node.interval or node.interval <= 0.0:
                self._cur_size -= 1
                self._push_timer_id(node.timer_id)
            else:
                while (node.timer_value - current_time) <= 0.005:
                    node.timer_value = node.timer_value + node.interval
                self._timer_queue.append(node)
            heapify(self._timer_queue)
            return node
        return None

    def _parse_crontab(self, entry, cron_entrys):
        """
        """
        if entry.lstrip().startswith('@'):
            entry = entry.strip()
            if entry == '@yearly': entry = "0 0 1 1 *"
            elif entry == '@monthly': entry = "0 0 1 * *"
            elif entry == '@weekly': entry = "0 0 * * 0"
            elif entry == '@daily': entry = "0 0 * * *"
            elif entry == '@hourly': entry = "0 * * * *"
            else: 
                raise (ValueError, "invalid entry [%s]" % entry)

        (min, hour, mday, month, wday) = entry.split()

        # parse time value 
        # Min
        cron_entrys['min'] = self._parse_crontab_entry(min, 
                                                       FIRST_MINUTE, 
                                                       LAST_MINUTE,
                                                       MINUTE_COUNT)
        # Hour
        cron_entrys['hour'] = self._parse_crontab_entry(hour, 
                                                       FIRST_HOUR, 
                                                       LAST_HOUR,
                                                       HOUR_COUNT)
        # Mday
        cron_entrys['mday'] = self._parse_crontab_entry(mday, 
                                                       FIRST_MDAY, 
                                                       LAST_MDAY,
                                                       MDAY_COUNT)
        # Month
        cron_entrys['month'] = self._parse_crontab_entry(month, 
                                                       FIRST_MONTH, 
                                                       LAST_MONTH,
                                                       MONTH_COUNT)
        # Wday
        cron_entrys['wday'] = self._parse_crontab_entry(wday, 
                                                       FIRST_WDAY, 
                                                       LAST_WDAY,
                                                       WDAY_COUNT)

    def _parse_crontab_entry(self, entry, first, end, count):
        """
        """
        time_list = []
        if entry.find(',') != -1:
            time_list.extend(self._get_list(entry, first, end, count)) 
        elif entry.find('-') != -1 and entry.find('/') != -1: # 3-9/2  
            time_list.extend(self._get_range_by_step(entry, first, end, count))
        elif entry.find('-') != -1:
            time_list.extend(self._get_list_by_range(entry, first, end, count))
        elif entry.find('/') != -1:
            time_list.extend(self._get_list_by_step(entry, first, end, count))
        else:
            time_list.extend(self._get_list_by_item(entry, first, end, count)) 

        s = set(time_list)
        time_list = list(s)
        time_list.sort()
        return time_list

    def _get_list(self, entry, first, end, count):
        """1,2,5-8,10,20-40/2"""

        items = filter(None, entry.split(','))  # avoid 1,,3,,
        lst = []
        for item in items:
            if item.find('-') != -1 and item.find('/') != -1:  # 3-9/2
                lst.extend(self._get_range_by_step(item, first, end, count))
            elif item.find('-') != -1:  # 3-5
                lst.extend(self._get_list_by_range(item, first, end, count))
            elif item.find('/') != -1: # 5/2
                lst.extend(self._get_list_by_step(item, first, end, count))
            else:
                lst.extend(self._get_list_by_item(item, first, end, count))
        return lst
    
    def _get_list_by_item(self, entry, first, end, count):
        """* or 2"""
        if entry.find('*') != -1: return list(range(first, count))
        n = int(entry)
        if n < first or n > end:
            raise (ValueError, "'%d' is out of range '%d~%d'" % (n, first, end))
        return [n]

    def _get_list_by_range(self, entry, first, end, count):
        """3-5"""
        items = [int(i) for i in entry.split('-') if i] # avoid 3--5
        if len(items) == 0:  # - -- --- 
            return list(range(first, count))
        elif len(items) == 1:  # open region
            if items[0] < first or items[0] > end:
                raise (ValueError, "'%d' is invalid time." % items[0])
            if entry.count('-') != 1:
                raise (ValueError, "'%s' is invalid format." % entry)
            if entry[0] == '-': 
                return list(range(first, items[0] + 1))
            return list(range(items[0], count))

        lst = items[0:2]
        if lst[0] < first or lst[0] > end:
            raise (ValueError, "'%d' is invalid time." % lst[0])
        if lst[1] < first or lst[1] > end:
            raise (ValueError, "'%d' is invalid time." % lst[1])
        if lst[0] > lst[-1]:
            ret = []
            for i in range(lst[0], lst[-1] + count):
                if i > end: i = i % (count - first)
                ret.append(i)
            return ret
        return list(range(lst[0], lst[-1] + 1))

    def _get_range_by_step(self, entry, first, end, count):  
        """3-9/2"""
        items = list(filter(None, entry.split('/')))  # avoid 3-9//2
        if len(items) == 0: 
            raise (ValueError, "bad entry [%d-%d]" % (first, end))
        elif len(items) == 1:  # 2-/  -/  -2/ 2-5/ 
            val = int(items[0])
            if val < first or val > end or val == 0:
                raise (ValueError, "'%d' is invalid time." % val)
            return self._get_list_by_range(val, first, end, count)
        l = self._get_list_by_range(items[0], first, end, count) 
        step = int(items[1])
        f = l[0]
        ret = []
        for i in l:
            if f in l: ret.append(f)
            if f + step > end:
                f = (f + step) % (count - first)
            else:
                f = (f + step) % count
        return ret

    def _get_list_by_step(self, entry, first, end, count):
        """*/2  or 3/2"""
        items = list(filter(None, entry.split('/')))
        if len(items) < 1: 
            raise (ValueError, "bad entry [%d-%d]" % (first, end))
        elif len(items) == 1:  # */ /3 3/
            if items[0] == '*': 
                return list(range(first, count))
            elif entry[0] == '/': 
                raise (ValueError, "bad entry [%d-%d]" % (first, end))
            else: return [int(items[0])]
        else: # */2 9/2
            if items[0] == '*': 
                val = int(items[1])
                if val > end or val < first or val == 0:
                    raise (ValueError, "'%d' is invalid time." % val)
                return list(range(first, count, int(items[1])))
            val = int(items[0])
            if val > end or val < first:
                raise (ValueError, "'%d' is invalid time." % val)
            return [val]

    def _build_timer_ids(self):
        """
        """
        self._timer_ids.extend(list(range(self._timer_id_index, \
                self._timer_id_index + _PRE_ALLOC_TIMER_ID_COUNT)))
        self._timer_id_index += _PRE_ALLOC_TIMER_ID_COUNT

    def _pop_timer_id(self):
        """
        """
        if not self._timer_ids:
            self._build_timer_ids()
        return self._timer_ids.popleft()

    def _push_timer_id(self, timerid):
        """
        """
        self._timer_ids.append(timerid)

