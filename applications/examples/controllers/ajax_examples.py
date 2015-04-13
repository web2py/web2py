def index():
    return dict()


def data():
    if not session.m:
        session.m = []
    if request.vars.q:
        if len(session.m) == 10:
            del(session.m[0])
        session.m.append(request.vars.q)
    return TABLE(*[TR(v) for v in sorted(session.m)]).xml()


def flash():
    response.flash = 'this text should appear!'
    return dict()


def fade():
    return dict()
