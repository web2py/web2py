


def counter():
    """ every time you reload, it increases the session.counter """

    if not session.counter:
        session.counter = 0
    session.counter += 1
    return dict(counter=session.counter)



