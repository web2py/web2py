def index():
    types = ['string','text','date','time','datetime','integer','double',
             'list:string','list:integer']
    db.define_table('mytable',*[Field('f_'+t.replace(':','_'),t) for t in types])
    return dict(        
        form = SQLFORM(db.mytable).process(),
        grid = SQLFORM.grid(db.mytable),
        )
