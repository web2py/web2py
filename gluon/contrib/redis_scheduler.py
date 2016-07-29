#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
| This file is part of the web2py Web Framework
| Created by niphlod@gmail.com
| License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Scheduler with redis backend
---------------------------------
"""
from __future__ import print_function

import os
import time
import socket
import datetime
import logging
from json import loads, dumps
from gluon.utils import web2py_uuid
from gluon.storage import Storage
from gluon.scheduler import *
from gluon.scheduler import _decode_dict
from gluon.contrib.redis_utils import RWatchError

USAGE = """
## Example

For any existing app

Create File: app/models/scheduler.py ======
from gluon.contrib.redis_utils import RConn
from gluon.contrib.redis_scheduler import RScheduler

def demo1(*args,**vars):
    print('you passed args=%s and vars=%s' % (args, vars))
    return 'done!'

def demo2():
    1/0

rconn = RConn()
mysched = RScheduler(db, dict(demo1=demo1,demo2=demo2), ...., redis_conn=rconn)

## run worker nodes with:

   cd web2py
   python web2py.py -K app

"""


path = os.getcwd()

if 'WEB2PY_PATH' not in os.environ:
    os.environ['WEB2PY_PATH'] = path

IDENTIFIER = "%s#%s" % (socket.gethostname(), os.getpid())

logger = logging.getLogger('web2py.scheduler.%s' % IDENTIFIER)

POLLING = 'POLLING'


class RScheduler(Scheduler):

    def __init__(self, db, tasks=None, migrate=True,
                 worker_name=None, group_names=None, heartbeat=HEARTBEAT,
                 max_empty_runs=0, discard_results=False, utc_time=False,
                 redis_conn=None, mode=1):

        """
        Highly-experimental coordination with redis
        Takes all args from Scheduler except redis_conn which
        must be something closer to a StrictRedis instance.

        My only regret - and the reason why I kept this under the hood for a
        while - is that it's hard to hook up in web2py to something happening
        right after the commit to a table, which will enable this version of the
        scheduler to process "immediate" tasks right away instead of waiting a
        few seconds (see FIXME in queue_task())

        mode is reserved for future usage patterns.
        Right now it moves the coordination (which is the most intensive
        routine in the scheduler in matters of IPC) of workers to redis.
        I'd like to have incrementally redis-backed modes of operations,
        such as e.g.:
            - 1: IPC through redis (which is the current implementation)
            - 2: Store task results in redis (which will relieve further pressure
                 from the db leaving the scheduler_run table empty and possibly
                 keep things smooth as tasks results can be set to expire
                 after a bit of time)
            - 3: Move all the logic for storing and queueing tasks to redis
                 itself - which means no scheduler_task usage too - and use
                 the database only as an historical record-bookkeeping
                 (e.g. for reporting)

        As usual, I'm eager to see your comments.
        """

        Scheduler.__init__(self, db, tasks=tasks, migrate=migrate,
                           worker_name=worker_name, group_names=group_names,
                           heartbeat=heartbeat, max_empty_runs=max_empty_runs,
                           discard_results=discard_results, utc_time=utc_time)

        self.r_server = redis_conn
        from gluon import current
        self._application = current.request.application or 'appname'

    def _nkey(self, key):
        """Helper to restrict all keys to a namespace and track them."""
        prefix = 'w2p:rsched:%s' % self._application
        allkeys = '%s:allkeys' % prefix
        newkey = "%s:%s" % (prefix, key)
        self.r_server.sadd(allkeys, newkey)
        return newkey

    def prune_all(self):
        """Global housekeeping."""
        all_keys = self._nkey('allkeys')
        with self.r_server.pipeline() as pipe:
            while True:
                try:
                    pipe.watch('PRUNE_ALL')
                    while True:
                        k = pipe.spop(all_keys)
                        if k is None:
                            break
                        pipe.delete(k)
                    pipe.execute()
                    break
                except RWatchError:
                    time.sleep(0.1)
                    continue

    def dt2str(self, value):
        return value.strftime('%Y-%m-%d %H:%M:%S')

    def str2date(self, value):
        return datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')

    def send_heartbeat(self, counter):
        """
        Workers coordination in redis.
        It has evolved into something is not that easy.
        Here we try to do what we need in a single transaction,
        and retry that transaction if something goes wrong
        """
        with self.r_server.pipeline() as pipe:
            while True:
                try:
                    pipe.watch('SEND_HEARTBEAT')
                    self.inner_send_heartbeat(counter, pipe)
                    pipe.execute()
                    self.adj_hibernation()
                    self.sleep()
                    break
                except RWatchError:
                    time.sleep(0.1)
                    continue

    def inner_send_heartbeat(self, counter, pipe):
        """
        Do a few things in the "maintenance" thread.

        Specifically:
        - registers the workers
        - accepts commands sent to workers (KILL, TERMINATE, PICK, DISABLED, etc)
        - adjusts sleep
        - saves stats
        - elects master
        - does "housecleaning" for dead workers
        - triggers tasks assignment
        """
        r_server = pipe
        status_keyset = self._nkey('worker_statuses')
        status_key = self._nkey('worker_status:%s' % (self.worker_name))
        now = self.now()
        mybackedstatus = r_server.hgetall(status_key)
        if not mybackedstatus:
            r_server.hmset(
                status_key,
                dict(
                    status=ACTIVE, worker_name=self.worker_name,
                    first_heartbeat=self.dt2str(now),
                    last_heartbeat=self.dt2str(now),
                    group_names=dumps(self.group_names), is_ticker=False,
                    worker_stats=dumps(self.w_stats))
            )
            r_server.sadd(status_keyset, status_key)
            if not self.w_stats.status == POLLING:
                self.w_stats.status = ACTIVE
                self.w_stats.sleep = self.heartbeat
                mybackedstatus = ACTIVE
        else:
            mybackedstatus = mybackedstatus['status']
            if mybackedstatus == DISABLED:
                # keep sleeping
                self.w_stats.status = DISABLED
                r_server.hmset(
                    status_key,
                    dict(last_heartbeat=self.dt2str(now),
                         worker_stats=dumps(self.w_stats))
                )
            elif mybackedstatus == TERMINATE:
                self.w_stats.status = TERMINATE
                logger.debug("Waiting to terminate the current task")
                self.give_up()
            elif mybackedstatus == KILL:
                self.w_stats.status = KILL
                self.die()
            else:
                if mybackedstatus == STOP_TASK:
                    logger.info('Asked to kill the current task')
                    self.terminate_process()
                logger.info('........recording heartbeat (%s)',
                            self.w_stats.status)
                r_server.hmset(
                    status_key,
                    dict(
                        last_heartbeat=self.dt2str(now), status=ACTIVE,
                        worker_stats=dumps(self.w_stats)
                    )
                )
                # newroutine
                r_server.expire(status_key, self.heartbeat * 3 * 15)
                self.w_stats.sleep = self.heartbeat  # re-activating the process
                if self.w_stats.status not in (RUNNING, POLLING):
                    self.w_stats.status = ACTIVE

            self.do_assign_tasks = False
            if counter % 5 == 0 or mybackedstatus == PICK:
                try:
                    logger.info(
                        '    freeing workers that have not sent heartbeat')
                    registered_workers = r_server.smembers(status_keyset)
                    allkeys = self._nkey('allkeys')
                    for worker in registered_workers:
                        w = r_server.hgetall(worker)
                        w = Storage(w)
                        if not w:
                            r_server.srem(status_keyset, worker)
                            logger.info('removing %s from %s', worker, allkeys)
                            r_server.srem(allkeys, worker)
                            continue
                    try:
                        self.is_a_ticker = self.being_a_ticker(pipe)
                    except:
                        pass
                    if self.w_stats.status in (ACTIVE, POLLING):
                        self.do_assign_tasks = True
                    if self.is_a_ticker and self.do_assign_tasks:
                        # I'm a ticker, and 5 loops passed without reassigning tasks,
                        # let's do that and loop again
                        if not self.db_thread:
                            logger.debug('thread building own DAL object')
                            self.db_thread = DAL(
                                self.db._uri, folder=self.db._adapter.folder)
                            self.define_tables(self.db_thread, migrate=False)
                        db = self.db_thread
                        self.wrapped_assign_tasks(db)
                        return None
                except:
                    logger.error('Error assigning tasks')

    def being_a_ticker(self, pipe):
        """
        Elects a ticker.

        This is slightly more convoluted than the original
        but if far more efficient
        """
        r_server = pipe
        status_keyset = self._nkey('worker_statuses')
        registered_workers = r_server.smembers(status_keyset)
        ticker = None
        all_active = []
        all_workers = []
        for worker in registered_workers:
            w = r_server.hgetall(worker)
            if w['worker_name'] != self.worker_name and w['status'] == ACTIVE:
                all_active.append(w)
                if w['is_ticker'] == 'True' and ticker is None:
                    ticker = w
            all_workers.append(w)
        not_busy = self.w_stats.status in (ACTIVE, POLLING)
        if not ticker:
            if not_busy:
                # only if this worker isn't busy, otherwise wait for a free one
                for worker in all_workers:
                    key = self._nkey('worker_status:%s' % worker['worker_name'])
                    if worker['worker_name'] == self.worker_name:
                        r_server.hset(key, 'is_ticker', True)
                    else:
                        r_server.hset(key, 'is_ticker', False)
                logger.info("TICKER: I'm a ticker")
            else:
                # giving up, only if I'm not alone
                if len(all_active) > 1:
                    key = self._nkey('worker_status:%s' % (self.worker_name))
                    r_server.hset(key, 'is_ticker', False)
                else:
                    not_busy = True
            return not_busy
        else:
            logger.info(
                "%s is a ticker, I'm a poor worker" % ticker['worker_name'])
            return False

    def assign_tasks(self, db):
        """
        The real beauty.

        We don't need to ASSIGN tasks, we just put
        them into the relevant queue
        """
        st, sd = db.scheduler_task, db.scheduler_task_deps
        r_server = self.r_server
        now = self.now()
        status_keyset = self._nkey('worker_statuses')
        with r_server.pipeline() as pipe:
            while True:
                try:
                    # making sure we're the only one doing the job
                    pipe.watch('ASSIGN_TASKS')
                    registered_workers = pipe.smembers(status_keyset)
                    all_workers = []
                    for worker in registered_workers:
                        w = pipe.hgetall(worker)
                        if w['status'] == ACTIVE:
                            all_workers.append(Storage(w))
                    pipe.execute()
                    break
                except RWatchError:
                    time.sleep(0.1)
                    continue

        # build workers as dict of groups
        wkgroups = {}
        for w in all_workers:
            group_names = loads(w.group_names)
            for gname in group_names:
                if gname not in wkgroups:
                    wkgroups[gname] = dict(
                        workers=[{'name': w.worker_name, 'c': 0}])
                else:
                    wkgroups[gname]['workers'].append(
                        {'name': w.worker_name, 'c': 0})
        # set queued tasks that expired between "runs" (i.e., you turned off
        # the scheduler): then it wasn't expired, but now it is
        db(
            (st.status.belongs((QUEUED, ASSIGNED))) &
            (st.stop_time < now)
        ).update(status=EXPIRED)

        # calculate dependencies
        deps_with_no_deps = db(
            (sd.can_visit == False) &
            (~sd.task_child.belongs(
                db(sd.can_visit == False)._select(sd.task_parent)
            )
            )
        )._select(sd.task_child)
        no_deps = db(
            (st.status.belongs((QUEUED, ASSIGNED))) &
            (
                (sd.id == None) | (st.id.belongs(deps_with_no_deps))

            )
        )._select(st.id, distinct=True, left=sd.on(
                 (st.id == sd.task_parent) &
                 (sd.can_visit == False)
        )
        )

        all_available = db(
            (st.status.belongs((QUEUED, ASSIGNED))) &
            (st.next_run_time <= now) &
            (st.enabled == True) &
            (st.id.belongs(no_deps))
        )

        limit = len(all_workers) * (50 / (len(wkgroups) or 1))

        # let's freeze it up
        db.commit()
        x = 0
        r_server = self.r_server
        for group in wkgroups.keys():
            queued_list = self._nkey('queued:%s' % group)
            queued_set = self._nkey('queued_set:%s' % group)
            # if are running, let's don't assign them again
            running_list = self._nkey('running:%s' % group)
            while True:
                # the joys for rpoplpush!
                t = r_server.rpoplpush(running_list, queued_list)
                if not t:
                    # no more
                    break
                r_server.sadd(queued_set, t)

            tasks = all_available(st.group_name == group).select(
                limitby=(0, limit), orderby = st.next_run_time)

            # put tasks in the processing list

            for task in tasks:
                x += 1
                gname = task.group_name

                if r_server.sismember(queued_set, task.id):
                    # already queued, we don't put on the list
                    continue
                r_server.sadd(queued_set, task.id)
                r_server.lpush(queued_list, task.id)
                d = dict(status=QUEUED)
                if not task.task_name:
                    d['task_name'] = task.function_name
                db(
                    (st.id == task.id) &
                    (st.status.belongs((QUEUED, ASSIGNED)))
                ).update(**d)
            db.commit()
        # I didn't report tasks but I'm working nonetheless!!!!
        if x > 0:
            self.w_stats.empty_runs = 0
        self.w_stats.queue = x
        self.w_stats.distribution = wkgroups
        self.w_stats.workers = len(all_workers)
        # I'll be greedy only if tasks queued are equal to the limit
        # (meaning there could be others ready to be queued)
        self.greedy = x >= limit
        logger.info('TICKER: workers are %s', len(all_workers))
        logger.info('TICKER: tasks are %s', x)

    def pop_task(self, db):
        """Lift a task off a queue."""
        r_server = self.r_server
        st = self.db.scheduler_task
        task = None
        # ready to process something
        for group in self.group_names:
            queued_set = self._nkey('queued_set:%s' % group)
            queued_list = self._nkey('queued:%s' % group)
            running_list = self._nkey('running:%s' % group)
            running_dict = self._nkey('running_dict:%s' % group)
            self.w_stats.status = POLLING
            # polling for 1 minute in total. If more groups are in,
            # polling is 1 minute in total
            logger.debug('    polling on %s', group)
            task_id = r_server.brpoplpush(queued_list, running_list,
                                          timeout=60 / len(self.group_names))
            logger.debug('    finished polling')
            self.w_stats.status = ACTIVE
            if task_id:
                r_server.hset(running_dict, task_id, self.worker_name)
                r_server.srem(queued_set, task_id)
                task = db(
                    (st.id == task_id) &
                    (st.status == QUEUED)
                ).select().first()
                if not task:
                    r_server.lrem(running_list, 0, task_id)
                    r_server.hdel(running_dict, task_id)
                    r_server.lrem(queued_list, 0, task_id)
                    logger.error("we received a task that isn't there (%s)",
                                 task_id)
                    return None
                break
        now = self.now()
        if task:
            task.update_record(status=RUNNING, last_run_time=now)
            # noone will touch my task!
            db.commit()
            logger.debug('   work to do %s', task.id)
        else:
            logger.info('nothing to do')
            return None
        times_run = task.times_run + 1
        if task.cronline:
            cron_recur = CronParser(task.cronline, now.replace(second=0))
            next_run_time = cron_recur.get_next()
        elif not task.prevent_drift:
            next_run_time = task.last_run_time + datetime.timedelta(
                seconds=task.period
            )
        else:
            # calc next_run_time based on available slots
            # see #1191
            next_run_time = task.start_time
            secondspassed = self.total_seconds(now - next_run_time)
            steps = secondspassed // task.period + 1
            next_run_time += datetime.timedelta(seconds=task.period * steps)

        if times_run < task.repeats or task.repeats == 0:
            # need to run (repeating task)
            run_again = True
        else:
            # no need to run again
            run_again = False
        run_id = 0
        while True and not self.discard_results:
            logger.debug('    new scheduler_run record')
            try:
                run_id = db.scheduler_run.insert(
                    task_id=task.id,
                    status=RUNNING,
                    start_time=now,
                    worker_name=self.worker_name)
                db.commit()
                break
            except:
                time.sleep(0.5)
                db.rollback()
        logger.info('new task %(id)s "%(task_name)s"'
                    ' %(application_name)s.%(function_name)s' % task)
        return Task(
            app=task.application_name,
            function=task.function_name,
            timeout=task.timeout,
            args=task.args,  # in json
            vars=task.vars,  # in json
            task_id=task.id,
            run_id=run_id,
            run_again=run_again,
            next_run_time=next_run_time,
            times_run=times_run,
            stop_time=task.stop_time,
            retry_failed=task.retry_failed,
            times_failed=task.times_failed,
            sync_output=task.sync_output,
            uuid=task.uuid,
            group_name=task.group_name)

    def report_task(self, task, task_report):
        """
        Override.

        Needs it only because we need to pop from the
        running tasks
        """
        r_server = self.r_server
        db = self.db
        now = self.now()
        st = db.scheduler_task
        sr = db.scheduler_run
        if not self.discard_results:
            if task_report.result != 'null' or task_report.tb:
                # result is 'null' as a string if task completed
                # if it's stopped it's None as NoneType, so we record
                # the STOPPED "run" anyway
                logger.debug(' recording task report in db (%s)',
                             task_report.status)
                db(sr.id == task.run_id).update(
                    status=task_report.status,
                    stop_time=now,
                    run_result=task_report.result,
                    run_output=task_report.output,
                    traceback=task_report.tb)
            else:
                logger.debug(' deleting task report in db because of no result')
                db(sr.id == task.run_id).delete()
        # if there is a stop_time and the following run would exceed it
        is_expired = (task.stop_time and
                      task.next_run_time > task.stop_time and
                      True or False)
        status = (task.run_again and is_expired and EXPIRED or
                  task.run_again and not is_expired and
                  QUEUED or COMPLETED)
        if task_report.status == COMPLETED:
            # assigned calculations
            d = dict(status=status,
                     next_run_time=task.next_run_time,
                     times_run=task.times_run,
                     times_failed=0,
                     assigned_worker_name=self.worker_name
                     )
            db(st.id == task.task_id).update(**d)
            if status == COMPLETED:
                self.update_dependencies(db, task.task_id)
        else:
            st_mapping = {'FAILED': 'FAILED',
                          'TIMEOUT': 'TIMEOUT',
                          'STOPPED': 'FAILED'}[task_report.status]
            status = (task.retry_failed and
                      task.times_failed < task.retry_failed and
                      QUEUED or task.retry_failed == -1 and
                      QUEUED or st_mapping)
            db(st.id == task.task_id).update(
                times_failed=st.times_failed + 1,
                next_run_time=task.next_run_time,
                status=status,
                assigned_worker_name=self.worker_name
            )
        logger.info('task completed (%s)', task_report.status)
        running_list = self._nkey('running:%s' % task.group_name)
        running_dict = self._nkey('running_dict:%s' % task.group_name)
        r_server.lrem(running_list, 0, task.task_id)
        r_server.hdel(running_dict, task.task_id)

    def wrapped_pop_task(self):
        """Commodity function to call `pop_task` and trap exceptions.
        If an exception is raised, assume it happened because of database
        contention and retries `pop_task` after 0.5 seconds
        """
        db = self.db
        db.commit()  # another nifty db.commit() only for Mysql
        x = 0
        while x < 10:
            try:
                rtn = self.pop_task(db)
                return rtn
                break
            # this is here to "interrupt" any blrpoplpush op easily
            except KeyboardInterrupt:
                self.give_up()
                break
            except:
                self.w_stats.errors += 1
                db.rollback()
                logger.error('    error popping tasks')
                x += 1
                time.sleep(0.5)

    def get_workers(self, only_ticker=False):
        """Return a dict holding worker_name : {**columns}
        representing all "registered" workers.
        only_ticker returns only the worker running as a TICKER,
        if there is any
        """
        r_server = self.r_server
        status_keyset = self._nkey('worker_statuses')
        registered_workers = r_server.smembers(status_keyset)
        all_workers = {}
        for worker in registered_workers:
            w = r_server.hgetall(worker)
            w = Storage(w)
            if not w:
                continue
            all_workers[w.worker_name] = Storage(
                status=w.status,
                first_heartbeat=self.str2date(w.first_heartbeat),
                last_heartbeat=self.str2date(w.last_heartbeat),
                group_names=loads(w.group_names, object_hook=_decode_dict),
                is_ticker=w.is_ticker == 'True' and True or False,
                worker_stats=loads(w.worker_stats, object_hook=_decode_dict)
            )
        if only_ticker:
            for k, v in all_workers.iteritems():
                if v['is_ticker']:
                    return {k: v}
            return {}
        return all_workers

    def set_worker_status(self, group_names=None, action=ACTIVE,
                          exclude=None, limit=None, worker_name=None):
        """Internal function to set worker's status"""
        r_server = self.r_server
        all_workers = self.get_workers()
        if not group_names:
            group_names = self.group_names
        elif isinstance(group_names, str):
            group_names = [group_names]
        exclusion = exclude and exclude.append(action) or [action]
        workers = []
        if worker_name is not None:
            if worker_name in all_workers.keys():
                workers = [worker_name]
        else:
            for k, v in all_workers.iteritems():
                if v.status not in exclusion and set(group_names) & set(v.group_names):
                    workers.append(k)
        if limit and worker_name is None:
            workers = workers[:limit]
        if workers:
            with r_server.pipeline() as pipe:
                while True:
                    try:
                        pipe.watch('SET_WORKER_STATUS')
                        for w in workers:
                            worker_key = self._nkey('worker_status:%s' % w)
                            pipe.hset(worker_key, 'status', action)
                        pipe.execute()
                        break
                    except RWatchError:
                        time.sleep(0.1)
                        continue

    def queue_task(self, function, pargs=[], pvars={}, **kwargs):
        """
        FIXME: immediate should put item in queue. The hard part is
        that currently there are no hooks happening at post-commit time
        Queue tasks. This takes care of handling the validation of all
        parameters

        Args:
            function: the function (anything callable with a __name__)
            pargs: "raw" args to be passed to the function. Automatically
                jsonified.
            pvars: "raw" kwargs to be passed to the function. Automatically
                jsonified
            kwargs: all the parameters available (basically, every
                `scheduler_task` column). If args and vars are here, they should
                be jsonified already, and they will override pargs and pvars

        Returns:
            a dict just as a normal validate_and_insert(), plus a uuid key
            holding the uuid of the queued task. If validation is not passed
            ( i.e. some parameters are invalid) both id and uuid will be None,
            and you'll get an "error" dict holding the errors found.
        """
        if hasattr(function, '__name__'):
            function = function.__name__
        targs = 'args' in kwargs and kwargs.pop('args') or dumps(pargs)
        tvars = 'vars' in kwargs and kwargs.pop('vars') or dumps(pvars)
        tuuid = 'uuid' in kwargs and kwargs.pop('uuid') or web2py_uuid()
        tname = 'task_name' in kwargs and kwargs.pop('task_name') or function
        immediate = 'immediate' in kwargs and kwargs.pop('immediate') or None
        cronline = kwargs.get('cronline')
        kwargs.update(function_name=function,
            task_name=tname,
            args=targs,
            vars=tvars,
            uuid=tuuid)
        if cronline:
            try:
                start_time = kwargs.get('start_time', self.now)
                next_run_time = CronParser(cronline, start_time).get_next()
                kwargs.update(start_time=start_time, next_run_time=next_run_time)
            except:
                pass
        rtn = self.db.scheduler_task.validate_and_insert(**kwargs)
        if not rtn.errors:
            rtn.uuid = tuuid
            if immediate:
                r_server = self.r_server
                ticker = self.get_workers(only_ticker=True)
                if ticker.keys():
                    ticker = ticker.keys()[0]
                    with r_server.pipeline() as pipe:
                        while True:
                            try:
                                pipe.watch('SET_WORKER_STATUS')
                                worker_key = self._nkey('worker_status:%s' % ticker)
                                pipe.hset(worker_key, 'status', 'PICK')
                                pipe.execute()
                                break
                            except RWatchError:
                                time.sleep(0.1)
                                continue
        else:
            rtn.uuid = None
        return rtn

    def stop_task(self, ref):
        """Shortcut for task termination.

        If the task is RUNNING it will terminate it, meaning that status
        will be set as FAILED.

        If the task is QUEUED, its stop_time will be set as to "now",
            the enabled flag will be set to False, and the status to STOPPED

        Args:
            ref: can be

              - an integer : lookup will be done by scheduler_task.id
              - a string : lookup will be done by scheduler_task.uuid

        Returns:
            - 1 if task was stopped (meaning an update has been done)
            - None if task was not found, or if task was not RUNNING or QUEUED

        Note:
            Experimental
        """
        r_server = self.r_server
        st = self.db.scheduler_task
        if isinstance(ref, int):
            q = st.id == ref
        elif isinstance(ref, str):
            q = st.uuid == ref
        else:
            raise SyntaxError(
                "You can retrieve results only by id or uuid")
        task = self.db(q).select(st.id, st.status, st.group_name)
        task = task.first()
        rtn = None
        if not task:
            return rtn
        running_dict = self._nkey('running_dict:%s' % task.group_name)
        if task.status == 'RUNNING':
            worker_key = r_server.hget(running_dict, task.id)
            worker_key = self._nkey('worker_status:%s' % (worker_key))
            r_server.hset(worker_key, 'status', STOP_TASK)
        elif task.status == 'QUEUED':
            rtn = self.db(q).update(
                stop_time=self.now(),
                enabled=False,
                status=STOPPED)
        return rtn
