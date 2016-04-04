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
from fix_path import fix_sys_path


fix_sys_path(__file__)

from gluon.storage import Storage
from gluon.languages import translator
from gluon.scheduler import JobGraph, Scheduler
from gluon.dal import DAL


class BaseTestScheduler(unittest.TestCase):
    def setUp(self):
        self.db = None
        self.cleanfolder()
        from gluon import current
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
sched = Scheduler(sched_dal, max_empty_runs=20, migrate=False, heartbeat=1)
            """
        with open(fdest, 'w') as q:
            q.write(initlines)
            q.write(content)

    def exec_sched(self):
        import subprocess
        call_args = [sys.executable, 'web2py.py', '-K', 'welcome']
        ret = subprocess.call(call_args, env=dict(os.environ))
        return ret


class TestsForSchedulerRunner(testForSchedulerRunnerBase):

    def testBasic(self):
        s = Scheduler(self.db)
        foo = s.queue_task('foo')
        self.db.commit()
        self.writefunction(r"""
def foo():
    return 'a'
""")
        ret = self.exec_sched()
        # process finished just fine
        self.assertEqual(ret, 0)
        info = s.task_status(foo.id, output=True)
        self.assertEqual(info.result, 'a')

    def testRetryFailed(self):
        s = Scheduler(self.db)
        failed = s.queue_task('demo2', retry_failed=1, period=5)
        failed_consecutive = s.queue_task('demo8', retry_failed=2, repeats=2, period=5)
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
    print 'number of lines', num_of_lines
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
        info = s.task_status(failed.id)
        task_runs = self.db(self.db.scheduler_run.task_id == info.id).select()
        res = [
            ("task status failed", info.status == 'FAILED'),
            ("task times_run is 0", info.times_run == 0),
            ("task times_failed is 2", info.times_failed == 2),
            ("task ran 2 times only", len(task_runs) == 2),
            ("scheduler_run records are FAILED", (task_runs[0].status == task_runs[1].status == 'FAILED')),
            ("period is respected", (task_runs[1].start_time > task_runs[0].start_time + datetime.timedelta(seconds=info.period)))
        ]
        for a in res:
            self.assertEqual(a[1], True, msg=a[0])

        # failed consecutive - checks
        info = s.task_status(failed_consecutive.id)
        task_runs = self.db(self.db.scheduler_run.task_id == info.id).select()
        res = [
            ("task status completed", info.status == 'COMPLETED'),
            ("task times_run is 2", info.times_run == 2),
            ("task times_failed is 0", info.times_failed == 0),
            ("task ran 6 times", len(task_runs) == 6),
            ("scheduler_run records for COMPLETED is 2", len([run.status for run in task_runs if run.status == 'COMPLETED']) == 2),
            ("scheduler_run records for FAILED is 4", len([run.status for run in task_runs if run.status == 'FAILED']) == 4),
        ]
        for a in res:
            self.assertEqual(a[1], True, msg=a[0])

if __name__ == '__main__':
    unittest.main()
