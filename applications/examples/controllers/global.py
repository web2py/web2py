
session.forget()

response.menu = [['home', False, '/%s/default/index'
                  % request.application], ['docs', True,
                 '/%s/global/vars' % request.application]]


def vars():
    """the running controller function!"""

    if not request.args:
        (
            doc,
            keys,
            t,
            c,
            d,
            value,
            ) = (
            'Global variables',
            globals(),
            None,
            None,
            (),
            None,
            )
        (title, args) = ('globals()', '')
    elif len(request.args) < 3:
        args = '.'.join(request.args)
        try:
            doc = eval(args + '.__doc__')
        except:
            doc = 'no documentation'
        try:
            keys = eval('dir(%s)' % args)
        except:
            keys = []
        t = eval('type(%s)' % args)
        try:
            c = eval('%s.__class__' % args)
        except:
            c = None
        try:
            d = eval('%s.__bases__' % args)
        except:
            d = None
        title = args
        args += '.'
    else:
        raise HTTP(400)
    attributes = {}
    for key in keys:
        a = args + key
        if eval('isinstance(%s,SQLDB)' % a) or a == 'vars':
            continue
        try:
            doc1 = eval(a + '.__doc__')
        except:
            doc1 = 'no documentation'
        t1 = eval('type(%s)' % a)
        try:
            c1 = eval('%s.__class__' % a)
        except:
            c1 = None
        try:
            d1 = eval('%s.__bases__' % a)
        except:
            d1 = ()
        attributes[a] = (doc1, t1, c1, d1)
    return dict(
        title=title,
        args=args,
        t=t,
        c=c,
        d=d,
        doc=doc,
        attributes=attributes,
        )



