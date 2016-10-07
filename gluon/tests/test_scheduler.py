#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    Unit tests for gluon.scheduler
"""
import os
import unittest
import glob
import datetime
import sys

from gluon.storage import Storage
from gluon.languages import translator
from gluon.scheduler import JobGraph, Scheduler, CronParser
from gluon.dal import DAL


class BaseTestScheduler(unittest.TestCase):
    def setUp(self):
        self.db = None
        self.cleanfolder()
        from gluon.globals import current
        s = Storage({'application': 'welcome',
                     'folder': 'applications/welcome',
                     'controller': 'default'})
        current.request = s
        T = translator('', 'en')
        current.T = T
        self.db = DAL('sqlite://dummy2.db', check_reserved=['all'])

    def cleanfolder(self):
        if self.db:
            self.db.close()
        try:
            os.unlink('dummy2.db')
        except:
            pass
        tfiles = glob.glob('*_scheduler*.table')
        for a in tfiles:
            os.unlink(a)

    def tearDown(self):
        self.cleanfolder()
        try:
            self.inner_teardown()
        except:
            pass


class CronParserTest(unittest.TestCase):

    def testMinute(self):
        # minute asterisk
        base = datetime.datetime(2010, 1, 23, 12, 18)
        itr = CronParser('*/1 * * * *', base)
        n1 = itr.get_next()    # 19
        self.assertEqual(base.year, n1.year)
        self.assertEqual(base.month, n1.month)
        self.assertEqual(base.day, n1.day)
        self.assertEqual(base.hour, n1.hour)
        self.assertEqual(base.minute, n1.minute - 1)
        for i in range(39):  # ~ 58
            itr.get_next()
        n2 = itr.get_next()
        self.assertEqual(n2.minute, 59)
        n3 = itr.get_next()
        self.assertEqual(n3.minute, 0)
        self.assertEqual(n3.hour, 13)

        itr = CronParser('*/5 * * * *', base)
        n4 = itr.get_next()
        self.assertEqual(n4.minute, 20)
        for i in range(6):
            itr.get_next()
        n5 = itr.get_next()
        self.assertEqual(n5.minute, 55)
        n6 = itr.get_next()
        self.assertEqual(n6.minute, 0)
        self.assertEqual(n6.hour, 13)

        base = datetime.datetime(2010, 1, 23, 12, 18)
        itr = CronParser('4/34 * * * *', base)
        n7 = itr.get_next()
        self.assertEqual(n7.minute, 38)
        self.assertEqual(n7.hour, 12)
        n8 = itr.get_next()
        self.assertEqual(n8.minute, 4)
        self.assertEqual(n8.hour, 13)

    def testHour(self):
        base = datetime.datetime(2010, 1, 24, 12, 2)
        itr = CronParser('0 */3 * * *', base)
        n1 = itr.get_next()
        self.assertEqual(n1.hour, 15)
        self.assertEqual(n1.minute, 0)
        for i in range(2):
            itr.get_next()
        n2 = itr.get_next()
        self.assertEqual(n2.hour, 0)
        self.assertEqual(n2.day, 25)

    def testDay(self):
        base = datetime.datetime(2010, 2, 24, 12, 9)
        itr = CronParser('0 0 */3 * *', base)
        n1 = itr.get_next()
        # 1 4 7 10 13 16 19 22 25 28
        self.assertEqual(n1.day, 25)
        n2 = itr.get_next()
        self.assertEqual(n2.day, 28)
        n3 = itr.get_next()
        self.assertEqual(n3.day, 1)
        self.assertEqual(n3.month, 3)

        # test leap year
        base = datetime.datetime(1996, 2, 27)
        itr = CronParser('0 0 * * *', base)
        n1 = itr.get_next()
        self.assertEqual(n1.day, 28)
        self.assertEqual(n1.month, 2)
        n2 = itr.get_next()
        self.assertEqual(n2.day, 29)
        self.assertEqual(n2.month, 2)

        base2 = datetime.datetime(2000, 2, 27)
        itr2 = CronParser('0 0 * * *', base2)
        n3 = itr2.get_next()
        self.assertEqual(n3.day, 28)
        self.assertEqual(n3.month, 2)
        n4 = itr2.get_next()
        self.assertEqual(n4.day, 29)
        self.assertEqual(n4.month, 2)

    def testWeekDay(self):
        base = datetime.datetime(2010, 2, 25)
        itr = CronParser('0 0 * * sat', base)
        n1 = itr.get_next()
        self.assertEqual(n1.isoweekday(), 6)
        self.assertEqual(n1.day, 27)
        n2 = itr.get_next()
        self.assertEqual(n2.isoweekday(), 6)
        self.assertEqual(n2.day, 6)
        self.assertEqual(n2.month, 3)

        base = datetime.datetime(2010, 1, 25)
        itr = CronParser('0 0 1 * wed', base)
        n1 = itr.get_next()
        self.assertEqual(n1.month, 1)
        self.assertEqual(n1.day, 27)
        self.assertEqual(n1.year, 2010)
        n2 = itr.get_next()
        self.assertEqual(n2.month, 2)
        self.assertEqual(n2.day, 1)
        self.assertEqual(n2.year, 2010)
        n3 = itr.get_next()
        self.assertEqual(n3.month, 2)
        self.assertEqual(n3.day, 3)
        self.assertEqual(n3.year, 2010)

    def testMonth(self):
        base = datetime.datetime(2010, 1, 25)
        itr = CronParser('0 0 1 * *', base)
        n1 = itr.get_next()
        self.assertEqual(n1.month, 2)
        self.assertEqual(n1.day, 1)
        n2 = itr.get_next()
        self.assertEqual(n2.month, 3)
        self.assertEqual(n2.day, 1)
        for i in range(8):
            itr.get_next()
        n3 = itr.get_next()
        self.assertEqual(n3.month, 12)
        self.assertEqual(n3.year, 2010)
        n4 = itr.get_next()
        self.assertEqual(n4.month, 1)
        self.assertEqual(n4.year, 2011)

        base = datetime.datetime(2010, 1, 25)
        itr = CronParser('0 0 1 */4 *', base)
        n1 = itr.get_next()
        self.assertEqual(n1.month, 5)
        self.assertEqual(n1.day, 1)

        base = datetime.datetime(2010, 1, 25)
        itr = CronParser('0 0 1 1-3 *', base)
        n1 = itr.get_next()
        self.assertEqual(n1.month, 2)
        self.assertEqual(n1.day, 1)
        n2 = itr.get_next()
        self.assertEqual(n2.month, 3)
        self.assertEqual(n2.day, 1)
        n3 = itr.get_next()
        self.assertEqual(n3.month, 1)
        self.assertEqual(n3.day, 1)

    def testSundayToThursdayWithAlphaConversion(self):
        base = datetime.datetime(2010, 8, 25, 15, 56)
        itr = CronParser("30 22 * * sun-thu", base)
        n1 = itr.get_next()
        self.assertEqual(base.year, n1.year)
        self.assertEqual(base.month, n1.month)
        self.assertEqual(base.day, n1.day)
        self.assertEqual(22, n1.hour)
        self.assertEqual(30, n1.minute)

    def testISOWeekday(self):
        base = datetime.datetime(2010, 2, 25)
        itr = CronParser('0 0 * * 7', base)
        n1 = itr.get_next()
        self.assertEqual(n1.isoweekday(), 7)
        self.assertEqual(n1.day, 28)
        n2 = itr.get_next()
        self.assertEqual(n2.isoweekday(), 7)
        self.assertEqual(n2.day, 7)
        self.assertEqual(n2.month, 3)
        base = datetime.datetime(2010, 2, 22)
        itr = CronParser('0 0 * * */2', base)
        n1 = itr.get_next()
        self.assertEqual(n1.isoweekday(), 2)
        self.assertEqual(n1.day, 23)
        n2 = itr.get_next()
        self.assertEqual(n2.isoweekday(), 4)
        self.assertEqual(n2.day, 25)

    def testBug2(self):

        base = datetime.datetime(2012, 1, 1, 0, 0)
        itr = CronParser('0 * * 3 *', base)
        n1 = itr.get_next()
        self.assertEqual(n1.year, base.year)
        self.assertEqual(n1.month, 3)
        self.assertEqual(n1.day, base.day)
        self.assertEqual(n1.hour, base.hour)
        self.assertEqual(n1.minute, base.minute)

        n2 = itr.get_next()
        self.assertEqual(n2.year, base.year)
        self.assertEqual(n2.month, 3)
        self.assertEqual(n2.day, base.day)
        self.assertEqual(n2.hour, base.hour + 1)
        self.assertEqual(n2.minute, base.minute)

        n3 = itr.get_next()
        self.assertEqual(n3.year, base.year)
        self.assertEqual(n3.month, 3)
        self.assertEqual(n3.day, base.day)
        self.assertEqual(n3.hour, base.hour + 2)
        self.assertEqual(n3.minute, base.minute)

    def testBug3(self):
        base = datetime.datetime(2013, 3, 1, 12, 17, 34, 257877)
        c = CronParser('00 03 16,30 * *', base)

        n1 = c.get_next()
        self.assertEqual(n1.month, 3)
        self.assertEqual(n1.day, 16)

        n2 = c.get_next()
        self.assertEqual(n2.month, 3)
        self.assertEqual(n2.day, 30)

        n3 = c.get_next()
        self.assertEqual(n3.month, 4)
        self.assertEqual(n3.day, 16)

    def test_rangeGenerator(self):
        base = datetime.datetime(2013, 3, 4, 0, 0)
        itr = CronParser('1-9/2 0 1 * *', base)
        n1 = itr.get_next()
        n2 = itr.get_next()
        n3 = itr.get_next()
        n4 = itr.get_next()
        n5 = itr.get_next()
        self.assertEqual(n1.minute, 1)
        self.assertEqual(n2.minute, 3)
        self.assertEqual(n3.minute, 5)
        self.assertEqual(n4.minute, 7)
        self.assertEqual(n5.minute, 9)

    def test_iterGenerator(self):
        base = datetime.datetime(2013, 3, 4, 0, 0)
        itr = CronParser('1-9/2 0 1 * *', base)
        x = 0
        for n in itr:
            x += 1
            if x > 4:
                break
        self.assertEqual(n.minute, 9)

    def test_invalidcron(self):
        base = datetime.datetime(2013, 3, 4, 0, 0)
        itr = CronParser('5 4 31 2 *', base)
        self.assertRaises(ValueError, itr.get_next)
        itr = CronParser('* * 5-1 * *', base)
        self.assertRaises(ValueError, itr.get_next)
        itr = CronParser('* * * janu-jun *', base)
        self.assertRaises(KeyError, itr.get_next)
        itr = CronParser('* * * * * *', base)
        self.assertRaises(ValueError, itr.get_next)
        itr = CronParser('* * * *', base)
        self.assertRaises(ValueError, itr.get_next)

    def testLastDayOfMonth(self):
        base = datetime.datetime(2015, 9, 4)
        itr = CronParser('0 0 L * *', base)
        n1 = itr.get_next()
        self.assertEqual(n1.month, 9)
        self.assertEqual(n1.day, 30)
        n2 = itr.get_next()
        self.assertEqual(n2.month, 10)
        self.assertEqual(n2.day, 31)
        n3 = itr.get_next()
        self.assertEqual(n3.month, 11)
        self.assertEqual(n3.day, 30)
        n4 = itr.get_next()
        self.assertEqual(n4.month, 12)
        self.assertEqual(n4.day, 31)

        base = datetime.datetime(1996, 2, 27)
        itr = CronParser('0 0 L * *', base)
        n1 = itr.get_next()
        self.assertEqual(n1.day, 29)
        self.assertEqual(n1.month, 2)
        n2 = itr.get_next()
        self.assertEqual(n2.day, 31)
        self.assertEqual(n2.month, 3)

    def testSpecialExpr(self):
        base = datetime.datetime(2000, 1, 1)
        itr = CronParser('@yearly', base)
        n1 = itr.get_next()
        self.assertEqual(n1.day, 1)
        self.assertEqual(n1.month, 1)
        self.assertEqual(n1.year, base.year + 1)
        self.assertEqual(n1.hour, 0)
        self.assertEqual(n1.minute, 0)

        itr = CronParser('@annually', base)
        n1 = itr.get_next()
        self.assertEqual(n1.day, 1)
        self.assertEqual(n1.month, 1)
        self.assertEqual(n1.year, base.year + 1)
        self.assertEqual(n1.hour, 0)
        self.assertEqual(n1.minute, 0)

        itr = CronParser('@monthly', base)
        n1 = itr.get_next()
        self.assertEqual(n1.day, 1)
        self.assertEqual(n1.month, base.month + 1)
        self.assertEqual(n1.year, base.year)
        self.assertEqual(n1.hour, 0)
        self.assertEqual(n1.minute, 0)

        itr = CronParser('@weekly', base)
        n1 = itr.get_next()
        self.assertEqual(n1.day, 2)
        self.assertEqual(n1.month, base.month)
        self.assertEqual(n1.year, base.year)
        self.assertEqual(n1.hour, 0)
        self.assertEqual(n1.minute, 0)
        n2 = itr.get_next()
        self.assertEqual(n2.day, 9)
        self.assertEqual(n2.month, base.month)
        self.assertEqual(n2.year, base.year)
        self.assertEqual(n2.hour, 0)
        self.assertEqual(n2.minute, 0)
        n3 = itr.get_next()
        self.assertEqual(n3.day, 16)
        self.assertEqual(n3.month, base.month)
        self.assertEqual(n3.year, base.year)
        self.assertEqual(n3.hour, 0)
        self.assertEqual(n3.minute, 0)

        itr = CronParser('@daily', base)
        n1 = itr.get_next()
        self.assertEqual(n1.day, 2)
        self.assertEqual(n1.month, base.month)
        self.assertEqual(n1.year, base.year)
        self.assertEqual(n1.hour, 0)
        self.assertEqual(n1.minute, 0)

        itr = CronParser('@midnight', base)
        n1 = itr.get_next()
        self.assertEqual(n1.day, 2)
        self.assertEqual(n1.month, base.month)
        self.assertEqual(n1.year, base.year)
        self.assertEqual(n1.hour, 0)
        self.assertEqual(n1.minute, 0)

        itr = CronParser('@hourly', base)
        n1 = itr.get_next()
        self.assertEqual(n1.day, 1)
        self.assertEqual(n1.month, base.month)
        self.assertEqual(n1.year, base.year)
        self.assertEqual(n1.hour, 1)
        self.assertEqual(n1.minute, 0)



class TestsForJobGraph(BaseTestScheduler):

    def testJobGraph(self):
        s = Scheduler(self.db)
        myjob = JobGraph(self.db, 'job_1')
        fname = 'foo'
        # We have a few items to wear, and there's an "order" to respect...
        # Items are: watch, jacket, shirt, tie, pants, undershorts, belt, shoes, socks
        # Now, we can't put on the tie without wearing the shirt first, etc...
        watch = s.queue_task(fname, task_name='watch')
        jacket = s.queue_task(fname, task_name='jacket')
        shirt = s.queue_task(fname, task_name='shirt')
        tie = s.queue_task(fname, task_name='tie')
        pants = s.queue_task(fname, task_name='pants')
        undershorts = s.queue_task(fname, task_name='undershorts')
        belt = s.queue_task(fname, task_name='belt')
        shoes = s.queue_task(fname, task_name='shoes')
        socks = s.queue_task(fname, task_name='socks')
        # before the tie, comes the shirt
        myjob.add_deps(tie.id, shirt.id)
        # before the belt too comes the shirt
        myjob.add_deps(belt.id, shirt.id)
        # before the jacket, comes the tie
        myjob.add_deps(jacket.id, tie.id)
        # before the belt, come the pants
        myjob.add_deps(belt.id, pants.id)
        # before the shoes, comes the pants
        myjob.add_deps(shoes.id, pants.id)
        # before the pants, comes the undershorts
        myjob.add_deps(pants.id, undershorts.id)
        # before the shoes, comes the undershorts
        myjob.add_deps(shoes.id, undershorts.id)
        # before the jacket, comes the belt
        myjob.add_deps(jacket.id, belt.id)
        # before the shoes, comes the socks
        myjob.add_deps(shoes.id, socks.id)

        ## results in the following topological sort
        # 9,3,6 --> 4,5 --> 8,7 --> 2
        # socks, shirt, undershorts
        # tie, pants
        # shoes, belt
        # jacket
        known_toposort = [
            set([socks.id, shirt.id, undershorts.id]),
            set([tie.id, pants.id]),
            set([shoes.id, belt.id]),
            set([jacket.id])
        ]
        toposort = myjob.validate('job_1')
        self.assertEqual(toposort, known_toposort)
        # add a cyclic dependency, jacket to undershorts
        myjob.add_deps(undershorts.id, jacket.id)
        # no exceptions raised, but result None
        self.assertEqual(myjob.validate('job_1'), None)

    def testJobGraphFailing(self):
        s = Scheduler(self.db)
        myjob = JobGraph(self.db, 'job_1')
        fname = 'foo'
        # We have a few items to wear, and there's an "order" to respect...
        # Items are: watch, jacket, shirt, tie, pants, undershorts, belt, shoes, socks
        # Now, we can't put on the tie without wearing the shirt first, etc...
        watch = s.queue_task(fname, task_name='watch')
        jacket = s.queue_task(fname, task_name='jacket')
        shirt = s.queue_task(fname, task_name='shirt')
        tie = s.queue_task(fname, task_name='tie')
        pants = s.queue_task(fname, task_name='pants')
        undershorts = s.queue_task(fname, task_name='undershorts')
        belt = s.queue_task(fname, task_name='belt')
        shoes = s.queue_task(fname, task_name='shoes')
        socks = s.queue_task(fname, task_name='socks')
        # before the tie, comes the shirt
        myjob.add_deps(tie.id, shirt.id)
        # before the belt too comes the shirt
        myjob.add_deps(belt.id, shirt.id)
        # before the jacket, comes the tie
        myjob.add_deps(jacket.id, tie.id)
        # before the belt, come the pants
        myjob.add_deps(belt.id, pants.id)
        # before the shoes, comes the pants
        myjob.add_deps(shoes.id, pants.id)
        # before the pants, comes the undershorts
        myjob.add_deps(pants.id, undershorts.id)
        # before the shoes, comes the undershorts
        myjob.add_deps(shoes.id, undershorts.id)
        # before the jacket, comes the belt
        myjob.add_deps(jacket.id, belt.id)
        # before the shoes, comes the socks
        myjob.add_deps(shoes.id, socks.id)
        # add a cyclic dependency, jacket to undershorts
        myjob.add_deps(undershorts.id, jacket.id)
        # no exceptions raised, but result None
        self.assertEqual(myjob.validate('job_1'), None)
        # and no deps added
        deps_inserted = self.db(self.db.scheduler_task_deps.id>0).count()
        self.assertEqual(deps_inserted, 0)

    def testJobGraphDifferentJobs(self):
        s = Scheduler(self.db)
        myjob1 = JobGraph(self.db, 'job_1')
        myjob2 = JobGraph(self.db, 'job_2')
        fname = 'foo'
        # We have a few items to wear, and there's an "order" to respect...
        # Items are: watch, jacket, shirt, tie, pants, undershorts, belt, shoes, socks
        # Now, we can't put on the tie without wearing the shirt first, etc...
        watch = s.queue_task(fname, task_name='watch')
        jacket = s.queue_task(fname, task_name='jacket')
        shirt = s.queue_task(fname, task_name='shirt')
        tie = s.queue_task(fname, task_name='tie')
        pants = s.queue_task(fname, task_name='pants')
        undershorts = s.queue_task(fname, task_name='undershorts')
        belt = s.queue_task(fname, task_name='belt')
        shoes = s.queue_task(fname, task_name='shoes')
        socks = s.queue_task(fname, task_name='socks')
        # before the tie, comes the shirt
        myjob1.add_deps(tie.id, shirt.id)
        # before the belt too comes the shirt
        myjob1.add_deps(belt.id, shirt.id)
        # before the jacket, comes the tie
        myjob1.add_deps(jacket.id, tie.id)
        # before the belt, come the pants
        myjob1.add_deps(belt.id, pants.id)
        # before the shoes, comes the pants
        myjob2.add_deps(shoes.id, pants.id)
        # before the pants, comes the undershorts
        myjob2.add_deps(pants.id, undershorts.id)
        # before the shoes, comes the undershorts
        myjob2.add_deps(shoes.id, undershorts.id)
        # before the jacket, comes the belt
        myjob2.add_deps(jacket.id, belt.id)
        # before the shoes, comes the socks
        myjob2.add_deps(shoes.id, socks.id)
        # every job by itself can be completed
        self.assertNotEqual(myjob1.validate('job_1'), None)
        self.assertNotEqual(myjob1.validate('job_2'), None)
        # and, implicitly, every queued task can be too
        self.assertNotEqual(myjob1.validate(), None)
        # add a cyclic dependency, jacket to undershorts
        myjob2.add_deps(undershorts.id, jacket.id)
        # every job can still be completed by itself
        self.assertNotEqual(myjob1.validate('job_1'), None)
        self.assertNotEqual(myjob1.validate('job_2'), None)
        # but trying to see if every task will ever be completed fails
        self.assertEqual(myjob2.validate(), None)


class TestsForSchedulerAPIs(BaseTestScheduler):

    def testQueue_Task(self):

        def isnotqueued(result):
            self.assertEqual(result.id, None)
            self.assertEqual(result.uuid, None)
            self.assertEqual(len(result.errors.keys()) > 0, True)

        def isqueued(result):
            self.assertNotEqual(result.id, None)
            self.assertNotEqual(result.uuid, None)
            self.assertEqual(len(result.errors.keys()), 0)

        s = Scheduler(self.db)
        fname = 'foo'
        watch = s.queue_task(fname, task_name='watch')
        # queuing a task returns id, errors, uuid
        self.assertEqual(set(watch.keys()), set(['id', 'uuid', 'errors']))
        # queueing nothing isn't allowed
        self.assertRaises(TypeError, s.queue_task, *[])
        # passing pargs and pvars wrongly
        # # pargs as dict
        isnotqueued(s.queue_task(fname, dict(a=1), dict(b=1)))
        # # pvars as list
        isnotqueued(s.queue_task(fname, ['foo', 'bar'], ['foo', 'bar']))
        # two tasks with the same uuid won't be there
        isqueued(s.queue_task(fname, uuid='a'))
        isnotqueued(s.queue_task(fname, uuid='a'))
        # # #FIXME add here every parameter

    def testTask_Status(self):
        s = Scheduler(self.db)
        fname = 'foo'
        watch = s.queue_task(fname, task_name='watch')
        # fetch status by id
        by_id = s.task_status(watch.id)
        # fetch status by uuid
        by_uuid = s.task_status(watch.uuid)
        # fetch status by query
        by_query = s.task_status(self.db.scheduler_task.function_name == 'foo')
        self.assertEqual(by_id, by_uuid)
        self.assertEqual(by_id, by_query)
        # fetch status by anything else throws
        self.assertRaises(SyntaxError, s.task_status, *[[1, 2]])
        # adding output returns the joined set, plus "result"
        rtn = s.task_status(watch.id, output=True)
        self.assertEqual(set(rtn.keys()), set(['scheduler_run', 'scheduler_task', 'result']))


class testForSchedulerRunnerBase(BaseTestScheduler):

    def inner_teardown(self):
        from gluon import current
        fdest = os.path.join(current.request.folder, 'models', 'scheduler.py')
        os.unlink(fdest)
        additional_files = [
            os.path.join(current.request.folder, 'private', 'demo8.pholder'),
            os.path.join(current.request.folder, 'views', 'issue_1485_2.html'),
        ]
        for f in additional_files:
            try:
                os.unlink(f)
            except:
                pass

    def writeview(self, content, dest=None):
        from gluon import current
        fdest = os.path.join(current.request.folder, 'views', dest)
        with open(fdest, 'w') as q:
            q.write(content)

    def writefunction(self, content, initlines=None):
        from gluon import current
        fdest = os.path.join(current.request.folder, 'models', 'scheduler.py')
        if initlines is None:
            initlines = """
import os
import time
from gluon.scheduler import Scheduler
db_dal = os.path.abspath(os.path.join(request.folder, '..', '..', 'dummy2.db'))
sched_dal = DAL('sqlite://%s' % db_dal, folder=os.path.dirname(db_dal))
sched = Scheduler(sched_dal, max_empty_runs=15, migrate=False, heartbeat=1)
def termination():
    sched.terminate()
    sched_dal.commit()
            """
        with open(fdest, 'w') as q:
            q.write(initlines)
            q.write(content)

    def exec_sched(self):
        import subprocess
        call_args = [sys.executable, 'web2py.py', '--no-banner', '-D', '20','-K', 'welcome']
        ret = subprocess.call(call_args, env=dict(os.environ))
        return ret

    def fetch_results(self, sched, task):
        info = sched.task_status(task.id)
        task_runs = self.db(self.db.scheduler_run.task_id == task.id).select()
        return info, task_runs

    def exec_asserts(self, stmts, tag):
        for stmt in stmts:
            self.assertEqual(stmt[1], True, msg="%s - %s" % (tag, stmt[0]))


class TestsForSchedulerRunner(testForSchedulerRunnerBase):

    def testRepeats_and_Expired_and_Prio(self):
        s = Scheduler(self.db)
        repeats = s.queue_task('demo1', ['a', 'b'], dict(c=1, d=2), repeats=2, period=5)
        a_while_ago = datetime.datetime.now() - datetime.timedelta(seconds=60)
        expired = s.queue_task('demo4', stop_time=a_while_ago)
        prio1 = s.queue_task('demo1', ['scheduled_first'])
        prio2 = s.queue_task('demo1', ['scheduled_second'], next_run_time=a_while_ago)
        self.db.commit()
        self.writefunction(r"""
def demo1(*args,**vars):
    print('you passed args=%s and vars=%s' % (args, vars))
    return args[0]

def demo4():
    time.sleep(15)
    print("I'm printing something")
    return dict(a=1, b=2)
""")
        ret = self.exec_sched()
        self.assertEqual(ret, 0)
        # repeats check
        task, task_run = self.fetch_results(s, repeats)
        res = [
            ("task status completed", task.status == 'COMPLETED'),
            ("task times_run is 2", task.times_run == 2),
            ("task ran 2 times only", len(task_run) == 2),
            ("scheduler_run records are COMPLETED ", (task_run[0].status == task_run[1].status == 'COMPLETED')),
            ("period is respected", (task_run[1].start_time > task_run[0].start_time + datetime.timedelta(seconds=task.period)))
        ]
        self.exec_asserts(res, 'REPEATS')

        # expired check
        task, task_run = self.fetch_results(s, expired)
        res = [
            ("task status expired", task.status == 'EXPIRED'),
            ("task times_run is 0", task.times_run == 0),
            ("task didn't run at all", len(task_run) == 0)
        ]
        self.exec_asserts(res, 'EXPIRATION')

        # prio check
        task1 = s.task_status(prio1.id, output=True)
        task2 = s.task_status(prio2.id, output=True)
        res = [
            ("tasks status completed", task1.scheduler_task.status == task2.scheduler_task.status == 'COMPLETED'),
            ("priority2 was executed before priority1" , task1.scheduler_run.id > task2.scheduler_run.id)
        ]
        self.exec_asserts(res, 'PRIORITY')

    def testNoReturn_and_Timeout_and_Progress(self):
        s = Scheduler(self.db)
        noret1 = s.queue_task('demo5')
        noret2 = s.queue_task('demo3')
        timeout1 = s.queue_task('demo4', timeout=5)
        timeout2 = s.queue_task('demo4')
        progress = s.queue_task('demo6', sync_output=2)
        termination = s.queue_task('termination')
        self.db.commit()
        self.writefunction(r"""
def demo3():
    time.sleep(3)
    print(1/0)
    return None

def demo4():
    time.sleep(15)
    print("I'm printing something")
    return dict(a=1, b=2)

def demo5():
    time.sleep(3)
    print("I'm printing something")
    rtn = dict(a=1, b=2)

def demo6():
    time.sleep(5)
    print('50%')
    time.sleep(5)
    print('!clear!100%')
    return 1
""")
        ret = self.exec_sched()
        self.assertEqual(ret, 0)
        # noreturn check
        task1, task_run1 = self.fetch_results(s, noret1)
        task2, task_run2 = self.fetch_results(s, noret2)
        res = [
            ("tasks no_returns1 completed", task1.status == 'COMPLETED'),
            ("tasks no_returns2 failed", task2.status == 'FAILED'),
            ("no_returns1 doesn't have a scheduler_run record", len(task_run1) == 0),
            ("no_returns2 has a scheduler_run record FAILED", (len(task_run2) == 1 and task_run2[0].status == 'FAILED')),
        ]
        self.exec_asserts(res, 'NO_RETURN')

        # timeout check
        task1 = s.task_status(timeout1.id, output=True)
        task2 = s.task_status(timeout2.id, output=True)
        res = [
            ("tasks timeouts1 timeoutted", task1.scheduler_task.status == 'TIMEOUT'),
            ("tasks timeouts2 completed", task2.scheduler_task.status == 'COMPLETED')
        ]
        self.exec_asserts(res, 'TIMEOUT')

        # progress check
        task1 = s.task_status(progress.id, output=True)
        res = [
            ("tasks percentages completed", task1.scheduler_task.status == 'COMPLETED'),
            ("output contains only 100%", task1.scheduler_run.run_output.strip() == "100%")
        ]
        self.exec_asserts(res, 'PROGRESS')

    def testDrift_and_env_and_immediate(self):
        s = Scheduler(self.db)
        immediate = s.queue_task('demo1', ['a', 'b'], dict(c=1, d=2), immediate=True)
        env = s.queue_task('demo7')
        drift = s.queue_task('demo1', ['a', 'b'], dict(c=1, d=2), period=93, prevent_drift=True)
        termination = s.queue_task('termination')
        self.db.commit()
        self.writefunction(r"""
def demo1(*args,**vars):
    print('you passed args=%s and vars=%s' % (args, vars))
    return args[0]
import random
def demo7():
    time.sleep(random.randint(1,5))
    print(W2P_TASK, request.now)
    return W2P_TASK.id, W2P_TASK.uuid, W2P_TASK.run_id
""")
        ret = self.exec_sched()
        self.assertEqual(ret, 0)
        # immediate check, can only check that nothing breaks
        task1 = s.task_status(immediate.id)
        res = [
            ("tasks status completed", task1.status == 'COMPLETED'),
        ]
        self.exec_asserts(res, 'IMMEDIATE')

        # drift check
        task, task_run = self.fetch_results(s, drift)
        res = [
            ("task status completed", task.status == 'COMPLETED'),
            ("next_run_time is exactly start_time + period", (task.next_run_time == task.start_time + datetime.timedelta(seconds=task.period)))
        ]
        self.exec_asserts(res, 'DRIFT')

        # env check
        task1 = s.task_status(env.id, output=True)
        res = [
            ("task %s returned W2P_TASK correctly" % (task1.scheduler_task.id),  task1.result == [task1.scheduler_task.id, task1.scheduler_task.uuid, task1.scheduler_run.id]),
        ]
        self.exec_asserts(res, 'ENV')


    def testRetryFailed(self):
        s = Scheduler(self.db)
        failed = s.queue_task('demo2', retry_failed=1, period=1)
        failed_consecutive = s.queue_task('demo8', retry_failed=2, repeats=2, period=1)
        self.db.commit()
        self.writefunction(r"""
def demo2():
    1/0

def demo8():
    placeholder = os.path.join(request.folder, 'private', 'demo8.pholder')
    with open(placeholder, 'a') as g:
        g.write('\nplaceholder for demo8 created')
    num_of_lines = 0
    with open(placeholder) as f:
        num_of_lines = len([a for a in f.read().split('\n') if a])
    print('number of lines', num_of_lines)
    if num_of_lines <= 2:
       1/0
    else:
        os.unlink(placeholder)
    return 1
""")
        ret = self.exec_sched()
        # process finished just fine
        self.assertEqual(ret, 0)
        # failed - checks
        task, task_run = self.fetch_results(s, failed)
        res = [
            ("task status failed", task.status == 'FAILED'),
            ("task times_run is 0", task.times_run == 0),
            ("task times_failed is 2", task.times_failed == 2),
            ("task ran 2 times only", len(task_run) == 2),
            ("scheduler_run records are FAILED", (task_run[0].status == task_run[1].status == 'FAILED')),
            ("period is respected", (task_run[1].start_time > task_run[0].start_time + datetime.timedelta(seconds=task.period)))
        ]
        self.exec_asserts(res, 'FAILED')

        # failed consecutive - checks
        task, task_run = self.fetch_results(s, failed_consecutive)
        res = [
            ("task status completed", task.status == 'COMPLETED'),
            ("task times_run is 2", task.times_run == 2),
            ("task times_failed is 0", task.times_failed == 0),
            ("task ran 6 times", len(task_run) == 6),
            ("scheduler_run records for COMPLETED is 2", len([run.status for run in task_run if run.status == 'COMPLETED']) == 2),
            ("scheduler_run records for FAILED is 4", len([run.status for run in task_run if run.status == 'FAILED']) == 4),
        ]
        self.exec_asserts(res, 'FAILED_CONSECUTIVE')

    def testRegressions(self):
        s = Scheduler(self.db)
        huge_result = s.queue_task('demo10', retry_failed=1, period=1)
        issue_1485 = s.queue_task('issue_1485')
        termination = s.queue_task('termination')
        self.db.commit()
        self.writefunction(r"""
def demo10():
    res = 'a' * 99999
    return dict(res=res)

def issue_1485():
    return response.render('issue_1485.html', dict(variable='abc'))
""")
        self.writeview(r"""<span>{{=variable}}</span>""", 'issue_1485.html')
        ret = self.exec_sched()
        # process finished just fine
        self.assertEqual(ret, 0)
        # huge_result - checks
        task_huge = s.task_status(huge_result.id, output=True)
        res = [
            ("task status completed", task_huge.scheduler_task.status == 'COMPLETED'),
            ("task times_run is 1", task_huge.scheduler_task.times_run == 1),
            ("result is the correct one", task_huge.result == dict(res='a' * 99999))
        ]
        self.exec_asserts(res, 'HUGE_RESULT')

        task_issue_1485 = s.task_status(issue_1485.id, output=True)
        res = [
            ("task status completed", task_issue_1485.scheduler_task.status == 'COMPLETED'),
            ("task times_run is 1", task_issue_1485.scheduler_task.times_run == 1),
            ("result is the correct one", task_issue_1485.result == '<span>abc</span>')
        ]
        self.exec_asserts(res, 'issue_1485')


if __name__ == '__main__':
    unittest.main()
