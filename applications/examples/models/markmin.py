import gluon.template

markmin_dict = dict(
    code_python=lambda code: str(CODE(code)),
    template=lambda \
        code:gluon.template.render(code,context=globals()),
    sup=lambda \
        code:'<sup style="font-size:0.5em;">%s</sup>'%code,
    br=lambda n:'<br>'*int(n),
    groupdates=lambda group:group_feed_reader(group),
    )

def get_content(b=None,\
                c=request.controller,\
                f=request.function,\
                l='en',\
                format='markmin'):
    """Gets and renders the file in
    <app>/private/content/<lang>/<controller>/<function>/<block>.<format>
    """

    def openfile():
        import os
        path = os.path.join(request.folder,'private','content',l,c,f,b+'.'+format)
        return open(path)

    try:
        openedfile = openfile()
    except Exception, IOError:
        l='en'
        openedfile = openfile()

    if format == 'markmin':
        html = MARKMIN(str(T(openedfile.read())),markmin_dict)
    else:
        html = str(T(openedfile.read()))
    openedfile.close()

    return html

