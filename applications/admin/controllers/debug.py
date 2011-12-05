import sys
import cStringIO
import gluon.contrib.shell
import code, thread
from gluon.debug import communicate


if DEMO_MODE or MULTI_USER_MODE:
    session.flash = T('disabled in demo mode')
    redirect(URL('default','site'))

FE=10**9

def index():
    app = request.args(0) or 'admin'
    reset()
    # read buffer
    data = communicate()
    return dict(app=app,data=data)

def callback():
    app = request.args[0]
    command = request.vars.statement
    session['debug_commands:'+app].append(command)
    output = communicate(command)
    k = len(session['debug_commands:'+app]) - 1
    return '[%i] %s%s\n' % (k + 1, command, output)

def reset():
    app = request.args(0) or 'admin'
    session['debug_commands:'+app] = []
    return 'done'



