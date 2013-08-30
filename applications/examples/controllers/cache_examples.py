import time

response.view = 'cache_examples/generic.html'

def cache_in_ram():
    """cache the output of the lambda function in ram"""

    t = cache.ram('time', lambda: time.ctime(), time_expire=5)
    return dict(time=t, link=A('click to reload', _href=URL(r=request)))


def cache_on_disk():
    """cache the output of the lambda function on disk"""

    t = cache.disk('time', lambda: time.ctime(), time_expire=5)
    return dict(time=t, link=A('click to reload', _href=URL(r=request)))


def cache_in_ram_and_disk():
    """cache the output of the lambda function on disk and in ram"""

    t = cache.ram('time', lambda: cache.disk('time', lambda:
                  time.ctime(), time_expire=5), time_expire=5)
    return dict(time=t, link=A('click to reload', _href=URL(r=request)))


@cache(request.env.path_info, time_expire=5, cache_model=cache.ram)
def cache_controller_in_ram():
    """cache the output of the controller in ram"""

    t = time.ctime()
    return dict(time=t, link=A('click to reload', _href=URL(r=request)))


@cache(request.env.path_info, time_expire=5, cache_model=cache.disk)
def cache_controller_on_disk():
    """cache the output of the controller on disk"""

    t = time.ctime()
    return dict(time=t, link=A('click to reload', _href=URL(r=request)))


@cache(request.env.path_info, time_expire=5, cache_model=cache.ram)
def cache_controller_and_view():
    """cache the output of the controller rendered by the view in ram"""

    t = time.ctime()
    d = dict(time=t, link=A('click to reload', _href=URL(r=request)))
    return response.render(d)
