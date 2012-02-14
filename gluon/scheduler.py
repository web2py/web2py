#### WORK IN PROGRESS... NOT SUPPOSED TO WORK YET

USAGE = """
## Example

For any existing app

Create File: app/models/scheduler.py ======
from gluon.scheduler import Scheduler

def demo1(*args,**vars):
    print 'you passed args=%s and vars=%s' % (args, vars)
    return 'done!'

def demo2():
    1/0

scheduler = Scheduler(db,dict(demo1=demo1,demo2=demo2))
## run worker nodes with:

   cd web2py
   python gluon/scheduler.py -u sqlite://storage.sqlite \
                             -f applications/myapp/databases/ \
                             -t mytasks.py
(-h for info)
python scheduler.py -h

## schedule jobs using
http://127.0.0.1:8000/scheduler/appadmin/insert/db/scheduler_task

## monitor scheduled jobs
http://127.0.0.1:8000/scheduler/appadmin/select/db?query=db.scheduler_task.id>0

## view completed jobs
http://127.0.0.1:8000/scheduler/appadmin/select/db?query=db.scheduler_run.id>0

## view workers
http://127.0.0.1:8000/scheduler/appadmin/select/db?query=db.scheduler_worker.id>0

## Comments
"""

import os
import time
import multiprocessing
import sys
import cStringIO
import threading
import traceback
import signal
import socket
import datetime
import logging
import optparse

try:
    from gluon.contrib.simplejson import loads, dumps
except:
    from simplejson import loads, dumps

if 'WEB2PY_PATH' in os.environ:
    sys.path.append(os.environ['WEB2PY_PATH'])
else:
    os.environ['WEB2PY_PATH'] = os.getcwd()

from gluon import DAL, Field, IS_NOT_EMPTY, IS_IN_SET
from gluon.utils import web2py_uuid

QUEUED = 'QUEUED'
ASSIGNED = 'ASSIGNED'
RUNNING = 'RUNNING'
COMPLETED = 'COMPLETED'
FAILED = 'FAILED'
TIMEOUT = 'TIMEOUT'
STOPPED = 'STOPPED'
ACTIVE = 'ACTIVE'
INACTIVE = 'INACTIVE'
DISABLED = 'DISABLED'
SECONDS = 1
HEARTBEAT = 3*SECONDS

class Task(object):
    def __init__(self,app,function,timeout,args='[]',vars='{}',**kwargs):
        logging.debug(' new task allocated: %s.%s' % (app,function))
        self.app = app
        self.function = function
        self.timeout = timeout
        self.args = args # json
        self.vars = vars # json
        self.__dict__.update(kwargs)
    def __str__(self):
        return '<Task: %s>' % self.function

class TaskReport(object):
    def __init__(self,status,result=None,output=None,tb=None):
        logging.debug('    new task report: %s' % status)
        if tb:
            logging.debug('   traceback: %s' % tb)
        else:
            logging.debug('   result: %s' % result)
        self.status = status
        self.result = result
        self.output = output
        self.tb = tb
    def __str__(self):
        return '<TaskReport: %s>' % self.status

def demo_function(*argv,**kwargs):
    """ test function """
    for i in range(argv[0]):
        print 'click',i
        time.sleep(1)
    return 'done'

#the two functions below deal with simplejson decoding as unicode, esp for the dict decode
#and subsequent usage as function Keyword arguments unicode variable names won't work!
#borrowed from http://stackoverflow.com/questions/956867/how-to-get-string-objects-instead-unicode-ones-from-json-in-python
def _decode_list(lst):
    newlist = []
    for i in lst:
        if isinstance(i, unicode):
            i = i.encode('utf-8')
        elif isinstance(i, list):
            i = _decode_list(i)
        newlist.append(i)
    return newlist

def _decode_dict(dct):
    newdict = {}
    for k, v in dct.iteritems():
        if isinstance(k, unicode):
            k = k.encode('utf-8')
        if isinstance(v, unicode):
             v = v.encode('utf-8')
        elif isinstance(v, list):
            v = _decode_list(v)
        newdict[k] = v
    return newdict

def executor(queue,task):
    """ the background process """
    logging.debug('    task started')
    stdout, sys.stdout = sys.stdout, cStringIO.StringIO()
    try:
        if task.app:
            os.chdir(os.environ['WEB2PY_PATH'])
            from gluon.shell import env
            from gluon.dal import BaseAdapter
            from gluon import current
            level = logging.getLogger().getEffectiveLevel()
            logging.getLogger().setLevel(logging.WARN)
            _env = env(task.app,import_models=True)
            logging.getLogger().setLevel(level)
            scheduler = current._scheduler
            scheduler_tasks = current._scheduler.tasks
            _function = scheduler_tasks[task.function]
            globals().update(_env)
            args = loads(task.args)
            vars = loads(task.vars, object_hook=_decode_dict)
            result = dumps(_function(*args,**vars))
        else:
            ### for testing purpose only
            result = eval(task.function)(
                *loads(task.args, object_hook=_decode_dict),
                 **loads(task.vars, object_hook=_decode_dict))
        stdout, sys.stdout = sys.stdout, stdout
        queue.put(TaskReport(COMPLETED, result,stdout.getvalue()))
    except BaseException,e:
        sys.stdout = stdout
        tb = traceback.format_exc()
        queue.put(TaskReport(FAILED,tb=tb))

class MetaScheduler(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.process = None     # the backround process
        self.have_heartbeat = True   # set to False to kill
    def async(self,task):
        """
        starts the background process and returns:
        ('ok',result,output)
        ('error',exception,None)
        ('timeout',None,None)
        ('terminated',None,None)
        """
        queue = multiprocessing.Queue(maxsize=1)
        p = multiprocessing.Process(target=executor,args=(queue,task))
        self.process = p
        logging.debug('   task starting')
        p.start()
        try:
            p.join(task.timeout)
        except:
            p.terminate()
            p.join()
            self.have_heartbeat = False
            logging.debug('    task stopped')
            return TaskReport(STOPPED)
        if p.is_alive():
            p.terminate()
            p.join()
            logging.debug('    task timeout')
            return TaskReport(TIMEOUT)
        elif queue.empty():
            self.have_heartbeat = False
            logging.debug('    task stopped')
            return TaskReport(STOPPED)
        else:
            logging.debug('  task completed or failed')
            return queue.get()

    def die(self):
        logging.info('die!')
        self.have_heartbeat = False
        self.terminate_process()

    def terminate_process(self):
        try:
            self.process.terminate()
        except:
            pass # no process to terminate

    def run(self):
        """ the thread that sends heartbeat """
        counter = 0
        while self.have_heartbeat:
            self.send_heartbeat(counter)
            counter += 1

    def start_heartbeats(self):
        self.start()

    def send_heartbeat(self,counter):
        print 'thum'
        time.sleep(1)

    def pop_task(self):
        return Task(
            app = None,
            function = 'demo_function',
            timeout = 7,
            args = '[2]',
            vars = '{}')

    def report_task(self,task,task_report):
        print 'reporting task'
        pass

    def sleep(self):
        pass

    def loop(self):
        try:
            self.start_heartbeats()
            while True and self.have_heartbeat:
                logging.debug('looping...')
                task = self.pop_task()
                if task:
                    self.report_task(task,self.async(task))
                else:
                    logging.debug('sleeping...')
                    self.sleep()
        except KeyboardInterrupt:
            self.die()


TASK_STATUS = (QUEUED, RUNNING, COMPLETED, FAILED, TIMEOUT, STOPPED)
RUN_STATUS = (RUNNING, COMPLETED, FAILED, TIMEOUT, STOPPED)
WORKER_STATUS = (ACTIVE,INACTIVE,DISABLED)

class TYPE(object):
    """
    validator that check whether field is valid json and validate its type
    """

    def __init__(self,myclass=list,parse=False):
        self.myclass = myclass
        self.parse=parse

    def __call__(self,value):
        from gluon import current
        try:
            obj = loads(value)
        except:
            return (value,current.T('invalid json'))
        else:
            if isinstance(obj,self.myclass):
                if self.parse:
                    return (obj,None)
                else:
                    return (value,None)
            else:
                return (value,current.T('Not of type: %s') % self.myclass)

class Scheduler(MetaScheduler):
    def __init__(self,db,tasks={},migrate=True,
                 worker_name=None,group_names=None,heartbeat=HEARTBEAT):

        MetaScheduler.__init__(self)

        self.db = db
        self.db_thread = None
        self.tasks = tasks
        self.group_names = group_names or ['main']
        self.heartbeat = heartbeat
        self.worker_name = worker_name or socket.gethostname()+'#'+str(web2py_uuid())

        from gluon import current
        current._scheduler = self

        self.define_tables(db,migrate=migrate)

    def define_tables(self,db,migrate):
        from gluon import current
        logging.debug('defining tables (migrate=%s)' % migrate)
        now = datetime.datetime.now()
        db.define_table(
            'scheduler_task',
            Field('application_name',requires=IS_NOT_EMPTY(),
                  default=None,writable=False),
            Field('task_name',requires=IS_NOT_EMPTY()),
            Field('group_name',default='main',writable=False),
            Field('status',requires=IS_IN_SET(TASK_STATUS),
                  default=QUEUED,writable=False),
            Field('function_name',
                  requires=IS_IN_SET(sorted(self.tasks.keys()))),
            Field('args','text',default='[]',requires=TYPE(list)),
            Field('vars','text',default='{}',requires=TYPE(dict)),
            Field('enabled','boolean',default=True),
            Field('start_time','datetime',default=now),
            Field('next_run_time','datetime',default=now),
            Field('stop_time','datetime',default=now+datetime.timedelta(days=1)),
            Field('repeats','integer',default=1,comment="0=unlimted"),
            Field('period','integer',default=60,comment='seconds'),
            Field('timeout','integer',default=60,comment='seconds'),
            Field('times_run','integer',default=0,writable=False),
            Field('last_run_time','datetime',writable=False,readable=False),
            Field('assigned_worker_name',default='',writable=False),
            migrate=migrate,format='%(task_name)s')
        if hasattr(current,'request'):
            db.scheduler_task.application_name.default=current.request.application

        db.define_table(
            'scheduler_run',
            Field('scheduler_task','reference scheduler_task'),
            Field('status',requires=IS_IN_SET(RUN_STATUS)),
            Field('start_time','datetime'),
            Field('stop_time','datetime'),
            Field('output','text'),
            Field('result','text'),
            Field('traceback','text'),
            Field('worker_name',default=self.worker_name),
            migrate=migrate)

        db.define_table(
            'scheduler_worker',
            Field('worker_name'),
            Field('first_heartbeat','datetime'),
            Field('last_heartbeat','datetime'),
            Field('status',requires=IS_IN_SET(WORKER_STATUS)),
            migrate=migrate)
        db.commit()

    def loop(self,worker_name=None):
        MetaScheduler.loop(self)

    def pop_task(self):
        now = datetime.datetime.now()
        db, ts = self.db, self.db.scheduler_task
        try:
            logging.debug(' grabbing all queued tasks')
            all_available = db(ts.status.belongs((QUEUED,RUNNING)))\
                ((ts.times_run<ts.repeats)|(ts.repeats==0))\
                (ts.start_time<=now)\
                (ts.stop_time>now)\
                (ts.next_run_time<=now)\
                (ts.enabled==True)\
                (ts.assigned_worker_name.belongs((None,'',self.worker_name))) #None?
            number_grabbed = all_available.update(
                assigned_worker_name=self.worker_name,status=ASSIGNED)
            db.commit()
        except:
            number_grabbed = None
            db.rollback()
        if number_grabbed:
            logging.debug('  grabbed %s tasks' % number_grabbed)
            grabbed = db(ts.assigned_worker_name==self.worker_name)\
                (ts.status==ASSIGNED)
            task = grabbed.select(limitby=(0,1), orderby=ts.next_run_time).first()

            logging.debug('   releasing all but one (running)')
            if task:
                task.update_record(status=RUNNING,last_run_time=now)
                grabbed.update(assigned_worker_name='',status=QUEUED)
                db.commit()
        else:
            return None
        next_run_time = task.last_run_time + datetime.timedelta(seconds=task.period)
        times_run = task.times_run + 1
        if times_run < task.repeats or task.repeats==0:
            run_again = True
        else:
            run_again = False
        logging.debug('    new scheduler_run record')
        while True:
            try:
                run_id = db.scheduler_run.insert(
                    scheduler_task = task.id,
                    status=RUNNING,
                    start_time=now,
                    worker_name=self.worker_name)
                db.commit()
                break
            except:
                db.rollback
        logging.info('new task %(id)s "%(task_name)s" %(application_name)s.%(function_name)s' % task)
        return Task(
            app = task.application_name,
            function = task.function_name,
            timeout = task.timeout,
            args = task.args, #in json
            vars = task.vars, #in json
            task_id = task.id,
            run_id = run_id,
            run_again = run_again,
            next_run_time=next_run_time,
            times_run = times_run)

    def report_task(self,task,task_report):
        logging.debug(' recording task report in db (%s)' % task_report.status)
        db = self.db
        db(db.scheduler_run.id==task.run_id).update(
            status = task_report.status,
            stop_time = datetime.datetime.now(),
            result = task_report.result,
            output = task_report.output,
            traceback = task_report.tb)
        if task_report.status == COMPLETED:
            d = dict(status = task.run_again and QUEUED or COMPLETED,
                     next_run_time = task.next_run_time,
                     times_run = task.times_run,
                     assigned_worker_name = '')
        else:
            d = dict(
                assigned_worker_name = '',
                status = {'FAILED':'FAILED',
                          'TIMEOUT':'TIMEOUT',
                          'STOPPED':'QUEUED'}[task_report.status])
        db(db.scheduler_task.id==task.task_id)\
            (db.scheduler_task.status==RUNNING).update(**d)
        db.commit()
        logging.info('task completed (%s)' % task_report.status)

    def send_heartbeat(self,counter):
        if not self.db_thread:
            logging.debug('thread building own DAL object')
            self.db_thread = DAL(self.db._uri,folder = self.db._adapter.folder)
            self.define_tables(self.db_thread,migrate=False)
        try:
            db = self.db_thread
            sw, st = db.scheduler_worker, db.scheduler_task
            now = datetime.datetime.now()
            expiration = now-datetime.timedelta(seconds=self.heartbeat*3)
            # record heartbeat
            logging.debug('........recording heartbeat')
            if not db(sw.worker_name==self.worker_name)\
                    .update(last_heartbeat = now, status = ACTIVE):
                sw.insert(status = ACTIVE,worker_name = self.worker_name,
                          first_heartbeat = now,last_heartbeat = now)
            if counter % 10 == 0:
                # deallocate jobs assigned to inactive workers and requeue them
                logging.debug('    freeing workers that have not sent heartbeat')
                inactive_workers = db(sw.last_heartbeat<expiration)
                db(st.assigned_worker_name.belongs(
                        inactive_workers._select(sw.worker_name)))\
                        (st.status.belongs((RUNNING,ASSIGNED,QUEUED)))\
                        .update(assigned_worker_name='',status=QUEUED)
                inactive_workers.delete()
            db.commit()
        except:
            db.rollback()
        time.sleep(self.heartbeat)

    def sleep(self):
        time.sleep(self.heartbeat) # should only sleep until next available task

def main():
    """
    allows to run worker without python web2py.py .... by simply python this.py
    """
    parser = optparse.OptionParser()
    parser.add_option(
        "-w", "--worker_name", dest="worker_name", default=None,
        help="start a worker with name")
    parser.add_option(
        "-b", "--heartbeat",dest="heartbeat", default = 10,
        help="heartbeat time in seconds (default 10)")
    parser.add_option(
        "-L", "--logger_level",dest="logger_level",
        default = 'INFO',
        help="level of logging (DEBUG, INFO, WARNING, ERROR)")
    parser.add_option(
        "-g", "--group_names",dest="group_names",
        default = 'main',
        help="comma separated list of groups to be picked by the worker")
    parser.add_option(
        "-f", "--db_folder",dest="db_folder",
        default = '/Users/mdipierro/web2py/applications/scheduler/databases',
        help="location of the dal database folder")
    parser.add_option(
        "-u", "--db_uri",dest="db_uri",
        default = 'sqlite://storage.sqlite',
        help="database URI string (web2py DAL syntax)")
    parser.add_option(
        "-t", "--tasks",dest="tasks",default=None,
        help="file containing task files, must define" + \
            "tasks = {'task_name':(lambda: 'output')} or similar set of tasks")
    (options, args) = parser.parse_args()
    if not options.tasks or not options.db_uri:
        print USAGE
    if options.tasks:
        path,filename = os.path.split(options.tasks)
        if filename.endswith('.py'):
            filename = filename[:-3]
        sys.path.append(path)
        print 'importing tasks...'
        tasks = __import__(filename, globals(), locals(), [], -1).tasks
        print 'tasks found: '+', '.join(tasks.keys())
    else:
        tasks = {}
    group_names = [x.strip() for x in options.group_names.split(',')]

    logging.getLogger().setLevel(options.logger_level)

    print 'groups for this worker: '+', '.join(group_names)
    print 'connecting to database in folder: ' + options.db_folder or './'
    print 'using URI: '+options.db_uri
    db = DAL(options.db_uri,folder=options.db_folder)
    print 'instantiating scheduler...'
    scheduler=Scheduler(db = db,
                        worker_name = options.worker_name,
                        tasks = tasks,
                        migrate = True,
                        group_names = group_names,
                        heartbeat = options.heartbeat)
    print 'starting main worker loop...'
    scheduler.loop()

if __name__=='__main__':
    main()

