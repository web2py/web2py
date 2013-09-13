session.forget()

def get(args):
    if args[0].startswith('__'):
        return None
    try:
        obj = globals(),get(args[0])
        for k in range(1,len(args)):
            obj = getattr(obj,args[k])
        return obj
    except:
        return None

def vars():
    """the running controller function!"""
    title = '.'.join(request.args)
    attributes = {}
    if not request.args:
        (doc,keys,t,c,d,value)=('Global variables',globals(),None,None,[],None)
    elif len(request.args) < 3:
        obj = get(request.args)
        if obj:
            doc = getattr(obj,'__doc__','no documentation')
            keys = dir(obj)
            t = type(obj)
            c = getattr(obj,'__class__',None)
            d = getattr(obj,'__bases__',None)

            for key in keys:
                a = getattr(obj,key,None)
                if a and not isinstance(a,DAL):
                    doc1 = getattr(a, '__doc__', '')
                    t1 = type(a)
                    c1 = getattr(a,'__class__',None)
                    d1 = getattr(a,'__bases__',None)
                    key = '.'.join(request.args)+'.'+key
                    attributes[key] = (doc1, t1, c1, d1)
        else:
            doc = 'Unkown'
            keys = []
            t = c = d = None
    else:
        raise HTTP(400)
    return dict(
        title=title,
        args=request.args,
        t=t,
        c=c,
        d=d,
        doc=doc,
        attributes=attributes,
    )
