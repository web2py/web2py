# -*- coding: utf-8 -*-

# ##########################################################
# ## make sure administrator is on localhost
# ###########################################################

import os
import socket
import datetime
import copy
import gluon.contenttype
import gluon.fileutils

try:
    import pygraphviz as pgv
except ImportError:
    pgv = None

response.subtitle = 'Database Administration (appadmin)'

# ## critical --- make a copy of the environment

global_env = copy.copy(globals())
global_env['datetime'] = datetime

http_host = request.env.http_host.split(':')[0]
remote_addr = request.env.remote_addr
try:
    hosts = (http_host, socket.gethostname(),
             socket.gethostbyname(http_host),
             '::1', '127.0.0.1', '::ffff:127.0.0.1')
except:
    hosts = (http_host, )

if request.env.http_x_forwarded_for or request.is_https:
    session.secure()
elif (remote_addr not in hosts) and (remote_addr != "127.0.0.1"):
    raise HTTP(200, T('appadmin is disabled because insecure channel'))

if request.function in ('auth_manage','manage') and 'auth' in globals():
    auth.requires_membership(auth.settings.manager_group_role)(lambda: None)()
    menu = False
elif (request.application == 'admin' and not session.authorized) or \
        (request.application != 'admin' and not gluon.fileutils.check_credentials(request)):    
    redirect(URL('admin', 'default', 'index',
                 vars=dict(send=URL(args=request.args, vars=request.vars))))
else:
    menu = True

ignore_rw = True
response.view = 'appadmin.html'
if menu:
    response.menu = [[T('design'), False, URL('admin', 'default', 'design',
                 args=[request.application])], [T('db'), False,
                 URL('index')], [T('state'), False,
                 URL('state')], [T('cache'), False,
                 URL('ccache')]]

# ##########################################################
# ## auxiliary functions
# ###########################################################

if False and request.tickets_db:
    from gluon.restricted import TicketStorage
    ts = TicketStorage()
    ts._get_table(request.tickets_db, ts.tablename, request.application)

def get_databases(request):
    dbs = {}
    for (key, value) in global_env.items():
        cond = False
        try:
            cond = isinstance(value, GQLDB)
        except:
            cond = isinstance(value, SQLDB)
        if cond:
            dbs[key] = value
    return dbs


databases = get_databases(None)


def eval_in_global_env(text):
    exec ('_ret=%s' % text, {}, global_env)
    return global_env['_ret']


def get_database(request):
    if request.args and request.args[0] in databases:
        return eval_in_global_env(request.args[0])
    else:
        session.flash = T('invalid request')
        redirect(URL('index'))


def get_table(request):
    db = get_database(request)
    if len(request.args) > 1 and request.args[1] in db.tables:
        return (db, request.args[1])
    else:
        session.flash = T('invalid request')
        redirect(URL('index'))


def get_query(request):
    try:
        return eval_in_global_env(request.vars.query)
    except Exception:
        return None


def query_by_table_type(tablename, db, request=request):
    keyed = hasattr(db[tablename], '_primarykey')
    if keyed:
        firstkey = db[tablename][db[tablename]._primarykey[0]]
        cond = '>0'
        if firstkey.type in ['string', 'text']:
            cond = '!=""'
        qry = '%s.%s.%s%s' % (
            request.args[0], request.args[1], firstkey.name, cond)
    else:
        qry = '%s.%s.id>0' % tuple(request.args[:2])
    return qry


# ##########################################################
# ## list all databases and tables
# ###########################################################
def index():
    return dict(databases=databases)


# ##########################################################
# ## insert a new record
# ###########################################################


def insert():
    (db, table) = get_table(request)
    form = SQLFORM(db[table], ignore_rw=ignore_rw)
    if form.accepts(request.vars, session):
        response.flash = T('new record inserted')
    return dict(form=form, table=db[table])


# ##########################################################
# ## list all records in table and insert new record
# ###########################################################


def download():
    import os
    db = get_database(request)
    return response.download(request, db)


def csv():
    import gluon.contenttype
    response.headers['Content-Type'] = \
        gluon.contenttype.contenttype('.csv')
    db = get_database(request)
    query = get_query(request)
    if not query:
        return None
    response.headers['Content-disposition'] = 'attachment; filename=%s_%s.csv'\
        % tuple(request.vars.query.split('.')[:2])
    return str(db(query, ignore_common_filters=True).select())


def import_csv(table, file):
    table.import_from_csv_file(file)


def select():
    import re
    db = get_database(request)
    dbname = request.args[0]
    regex = re.compile('(?P<table>\w+)\.(?P<field>\w+)=(?P<value>\d+)')
    if len(request.args) > 1 and hasattr(db[request.args[1]], '_primarykey'):
        regex = re.compile('(?P<table>\w+)\.(?P<field>\w+)=(?P<value>.+)')
    if request.vars.query:
        match = regex.match(request.vars.query)
        if match:
            request.vars.query = '%s.%s.%s==%s' % (request.args[0],
                                                   match.group('table'), match.group('field'),
                                                   match.group('value'))
    else:
        request.vars.query = session.last_query
    query = get_query(request)
    if request.vars.start:
        start = int(request.vars.start)
    else:
        start = 0
    nrows = 0
    stop = start + 100
    table = None
    rows = []
    orderby = request.vars.orderby
    if orderby:
        orderby = dbname + '.' + orderby
        if orderby == session.last_orderby:
            if orderby[0] == '~':
                orderby = orderby[1:]
            else:
                orderby = '~' + orderby
    session.last_orderby = orderby
    session.last_query = request.vars.query
    form = FORM(TABLE(TR(T('Query:'), '', INPUT(_style='width:400px',
                _name='query', _value=request.vars.query or '',
                requires=IS_NOT_EMPTY(
                    error_message=T("Cannot be empty")))), TR(T('Update:'),
                INPUT(_name='update_check', _type='checkbox',
                value=False), INPUT(_style='width:400px',
                _name='update_fields', _value=request.vars.update_fields
                                    or '')), TR(T('Delete:'), INPUT(_name='delete_check',
                _class='delete', _type='checkbox', value=False), ''),
                TR('', '', INPUT(_type='submit', _value=T('submit')))),
                _action=URL(r=request, args=request.args))

    tb = None
    if form.accepts(request.vars, formname=None):
        regex = re.compile(request.args[0] + '\.(?P<table>\w+)\..+')
        match = regex.match(form.vars.query.strip())
        if match:
            table = match.group('table')
        try:
            nrows = db(query).count()
            if form.vars.update_check and form.vars.update_fields:
                db(query).update(**eval_in_global_env('dict(%s)'
                                                      % form.vars.update_fields))
                response.flash = T('%s %%{row} updated', nrows)
            elif form.vars.delete_check:
                db(query).delete()
                response.flash = T('%s %%{row} deleted', nrows)
            nrows = db(query).count()
            if orderby:
                rows = db(query, ignore_common_filters=True).select(limitby=(
                    start, stop), orderby=eval_in_global_env(orderby))
            else:
                rows = db(query, ignore_common_filters=True).select(
                    limitby=(start, stop))
        except Exception, e:
            import traceback
            tb = traceback.format_exc()
            (rows, nrows) = ([], 0)
            response.flash = DIV(T('Invalid Query'), PRE(str(e)))
    # begin handle upload csv
    csv_table = table or request.vars.table
    if csv_table:
        formcsv = FORM(str(T('or import from csv file')) + " ",
                       INPUT(_type='file', _name='csvfile'),
                       INPUT(_type='hidden', _value=csv_table, _name='table'),
                       INPUT(_type='submit', _value=T('import')))
    else:
        formcsv = None
    if formcsv and formcsv.process().accepted:
        try:
            import_csv(db[request.vars.table],
                       request.vars.csvfile.file)
            response.flash = T('data uploaded')
        except Exception, e:
            response.flash = DIV(T('unable to parse csv file'), PRE(str(e)))
    # end handle upload csv

    return dict(
        form=form,
        table=table,
        start=start,
        stop=stop,
        nrows=nrows,
        rows=rows,
        query=request.vars.query,
        formcsv=formcsv,
        tb=tb,
    )


# ##########################################################
# ## edit delete one record
# ###########################################################


def update():
    (db, table) = get_table(request)
    keyed = hasattr(db[table], '_primarykey')
    record = None
    db[table]._common_filter = None
    if keyed:
        key = [f for f in request.vars if f in db[table]._primarykey]
        if key:
            record = db(db[table][key[0]] == request.vars[key[
                        0]]).select().first()
    else:
        record = db(db[table].id == request.args(
            2)).select().first()

    if not record:
        qry = query_by_table_type(table, db)
        session.flash = T('record does not exist')
        redirect(URL('select', args=request.args[:1],
                     vars=dict(query=qry)))

    if keyed:
        for k in db[table]._primarykey:
            db[table][k].writable = False

    form = SQLFORM(
        db[table], record, deletable=True, delete_label=T('Check to delete'),
        ignore_rw=ignore_rw and not keyed,
        linkto=URL('select',
                   args=request.args[:1]), upload=URL(r=request,
                                                      f='download', args=request.args[:1]))

    if form.accepts(request.vars, session):
        session.flash = T('done!')
        qry = query_by_table_type(table, db)
        redirect(URL('select', args=request.args[:1],
                 vars=dict(query=qry)))
    return dict(form=form, table=db[table])


# ##########################################################
# ## get global variables
# ###########################################################


def state():
    return dict()


def ccache():
    cache.ram.initialize()
    cache.disk.initialize()

    form = FORM(
        P(TAG.BUTTON(
            T("Clear CACHE?"), _type="submit", _name="yes", _value="yes")),
        P(TAG.BUTTON(
            T("Clear RAM"), _type="submit", _name="ram", _value="ram")),
        P(TAG.BUTTON(
            T("Clear DISK"), _type="submit", _name="disk", _value="disk")),
    )

    if form.accepts(request.vars, session):
        clear_ram = False
        clear_disk = False
        session.flash = ""
        if request.vars.yes:
            clear_ram = clear_disk = True
        if request.vars.ram:
            clear_ram = True
        if request.vars.disk:
            clear_disk = True

        if clear_ram:
            cache.ram.clear()
            session.flash += T("Ram Cleared")
        if clear_disk:
            cache.disk.clear()
            session.flash += T("Disk Cleared")

        redirect(URL(r=request))

    try:
        from guppy import hpy
        hp = hpy()
    except ImportError:
        hp = False

    import shelve
    import os
    import copy
    import time
    import math
    from gluon import portalocker

    ram = {
        'entries': 0,
        'bytes': 0,
        'objects': 0,
        'hits': 0,
        'misses': 0,
        'ratio': 0,
        'oldest': time.time(),
        'keys': []
    }
    disk = copy.copy(ram)
    total = copy.copy(ram)
    disk['keys'] = []
    total['keys'] = []

    def GetInHMS(seconds):
        hours = math.floor(seconds / 3600)
        seconds -= hours * 3600
        minutes = math.floor(seconds / 60)
        seconds -= minutes * 60
        seconds = math.floor(seconds)

        return (hours, minutes, seconds)

    for key, value in cache.ram.storage.iteritems():
        if isinstance(value, dict):
            ram['hits'] = value['hit_total'] - value['misses']
            ram['misses'] = value['misses']
            try:
                ram['ratio'] = ram['hits'] * 100 / value['hit_total']
            except (KeyError, ZeroDivisionError):
                ram['ratio'] = 0
        else:
            if hp:
                ram['bytes'] += hp.iso(value[1]).size
                ram['objects'] += hp.iso(value[1]).count
            ram['entries'] += 1
            if value[0] < ram['oldest']:
                ram['oldest'] = value[0]
            ram['keys'].append((key, GetInHMS(time.time() - value[0])))
    folder = os.path.join(request.folder,'cache')
    if not os.path.exists(folder):
        os.mkdir(folder)
    locker = open(os.path.join(folder, 'cache.lock'), 'a')
    portalocker.lock(locker, portalocker.LOCK_EX)
    disk_storage = shelve.open(
        os.path.join(folder, 'cache.shelve'))
    try:
        for key, value in disk_storage.items():
            if isinstance(value, dict):
                disk['hits'] = value['hit_total'] - value['misses']
                disk['misses'] = value['misses']
                try:
                    disk['ratio'] = disk['hits'] * 100 / value['hit_total']
                except (KeyError, ZeroDivisionError):
                    disk['ratio'] = 0
            else:
                if hp:
                    disk['bytes'] += hp.iso(value[1]).size
                    disk['objects'] += hp.iso(value[1]).count
                disk['entries'] += 1
                if value[0] < disk['oldest']:
                    disk['oldest'] = value[0]
                disk['keys'].append((key, GetInHMS(time.time() - value[0])))

    finally:
        portalocker.unlock(locker)
        locker.close()
        disk_storage.close()

    total['entries'] = ram['entries'] + disk['entries']
    total['bytes'] = ram['bytes'] + disk['bytes']
    total['objects'] = ram['objects'] + disk['objects']
    total['hits'] = ram['hits'] + disk['hits']
    total['misses'] = ram['misses'] + disk['misses']
    total['keys'] = ram['keys'] + disk['keys']
    try:
        total['ratio'] = total['hits'] * 100 / (total['hits'] +
                                                total['misses'])
    except (KeyError, ZeroDivisionError):
        total['ratio'] = 0

    if disk['oldest'] < ram['oldest']:
        total['oldest'] = disk['oldest']
    else:
        total['oldest'] = ram['oldest']

    ram['oldest'] = GetInHMS(time.time() - ram['oldest'])
    disk['oldest'] = GetInHMS(time.time() - disk['oldest'])
    total['oldest'] = GetInHMS(time.time() - total['oldest'])

    def key_table(keys):
        return TABLE(
            TR(TD(B(T('Key'))), TD(B(T('Time in Cache (h:m:s)')))),
            *[TR(TD(k[0]), TD('%02d:%02d:%02d' % k[1])) for k in keys],
            **dict(_class='cache-keys',
                   _style="border-collapse: separate; border-spacing: .5em;"))

    ram['keys'] = key_table(ram['keys'])
    disk['keys'] = key_table(disk['keys'])
    total['keys'] = key_table(total['keys'])

    return dict(form=form, total=total,
                ram=ram, disk=disk, object_stats=hp != False)


def table_template(table):
    from gluon.html import TR, TD, TABLE, TAG

    def FONT(*args, **kwargs):
        return TAG.font(*args, **kwargs)

    def types(field):
        f_type = field.type
        if not isinstance(f_type,str):
            return ' '
        elif f_type == 'string':
            return field.length
        elif f_type == 'id':
            return B('pk')
        elif f_type.startswith('reference') or \
                f_type.startswith('list:reference'):
            return B('fk')
        else:
            return ' '

    # This is horribe HTML but the only one graphiz understands
    rows = []
    cellpadding = 4
    color = "#000000"
    bgcolor = "#FFFFFF"
    face = "Helvetica"
    face_bold = "Helvetica Bold"
    border = 0

    rows.append(TR(TD(FONT(table, _face=face_bold, _color=bgcolor),
                           _colspan=3, _cellpadding=cellpadding,
                           _align="center", _bgcolor=color)))
    for row in db[table]:
        rows.append(TR(TD(FONT(row.name, _color=color, _face=face_bold),
                              _align="left", _cellpadding=cellpadding,
                              _border=border),
                       TD(FONT(row.type, _color=color, _face=face),
                               _align="left", _cellpadding=cellpadding,
                               _border=border),
                       TD(FONT(types(row), _color=color, _face=face),
                               _align="center", _cellpadding=cellpadding,
                               _border=border)))
    return "< %s >" % TABLE(*rows, **dict(_bgcolor=bgcolor, _border=1,
                                          _cellborder=0, _cellspacing=0)
                             ).xml()


def bg_graph_model():
    graph = pgv.AGraph(layout='dot',  directed=True,  strict=False,  rankdir='LR')
    
    subgraphs = dict()    
    for tablename in db.tables:
        if hasattr(db[tablename],'_meta_graphmodel'):
            meta_graphmodel = db[tablename]._meta_graphmodel
        else:
            meta_graphmodel = dict(group='Undefined', color='#ECECEC')
        
        group = meta_graphmodel['group'].replace(' ', '') 
        if not subgraphs.has_key(group):
            subgraphs[group] = dict(meta=meta_graphmodel, tables=[])
            subgraphs[group]['tables'].append(tablename)
        else:
            subgraphs[group]['tables'].append(tablename)        
      
        graph.add_node(tablename, name=tablename, shape='plaintext',
                       label=table_template(tablename))
    
    for n, key in enumerate(subgraphs.iterkeys()):        
        graph.subgraph(nbunch=subgraphs[key]['tables'],
                    name='cluster%d' % n,
                    style='filled',
                    color=subgraphs[key]['meta']['color'],
                    label=subgraphs[key]['meta']['group'])   

    for tablename in db.tables:
        for field in db[tablename]:
            f_type = field.type
            if isinstance(f_type,str) and (
                f_type.startswith('reference') or
                f_type.startswith('list:reference')):
                referenced_table = f_type.split()[1].split('.')[0]
                n1 = graph.get_node(tablename)
                n2 = graph.get_node(referenced_table)
                graph.add_edge(n1, n2, color="#4C4C4C", label='')

    graph.layout()
    #return graph.draw(format='png', prog='dot')
    if not request.args:
        return graph.draw(format='png', prog='dot')
    else:       
        response.headers['Content-Disposition']='attachment;filename=graph.%s'%request.args(0)
        if request.args(0) == 'dot':        
            return graph.string()
        else:
            return graph.draw(format=request.args(0), prog='dot')

def graph_model():    
    return dict(databases=databases, pgv=pgv)

def auth_manage():
    tablename = request.args(0)
    if not tablename or not tablename in auth.db.tables:
        return dict()
    table = auth.db[tablename]
    formname = '%s_grid' % tablename
    if tablename == auth.settings.table_user_name:
        auth.settings.table_user._plural = T('Users')
        auth.settings.table_membership._plural = T('Roles')
        auth.settings.table_membership._id.readable = False
        auth.settings.table_membership.user_id.label = T('User')
        auth.settings.table_membership.group_id.label = T('Role')
        grid = SQLFORM.smartgrid(table, args=request.args[:1], user_signature=True,
                                 linked_tables=[auth.settings.table_membership_name],
                                 maxtextlength=1000, formname=formname)
    else:
        table._id.readable = False
        auth.settings.table_permission.group_id.label = T('Role')
        auth.settings.table_permission.name.label = T('Permission')
        orderby = 'role' if table == auth.settings.table_group_name else 'group_id'
        grid = SQLFORM.grid(table, args=request.args[:1], orderby=table[orderby],
                            user_signature=True, maxtextlength=1000, formname=formname)    
    return grid if request.extension=='load' else dict(grid=grid)

def manage():
    tablename = request.args(0)
    if tablename in auth.db.tables:
        grid = SQLFORM.smartgrid(auth.db[tablename], args=request.args[:1])
    else:
        return dict()
    return grid if request.extension=='load' else dict(grid=grid)
