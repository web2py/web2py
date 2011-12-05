def index():
    return dict()


def data():
    if not session.m or len(session.m) == 10:
        session.m = []
    if request.vars.q:
        session.m.append(request.vars.q)
    session.m.sort()
    return TABLE(*[TR(v) for v in session.m]).xml()


def flash():
    response.flash = 'this text should appear!'
    return dict()


def fade():
    return dict()



