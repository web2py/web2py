from gluon.contrib.spreadsheet import Sheet

def callback():
    return cache.ram('sheet1',lambda:None,None).process(request)

def index():
    sheet = cache.ram('sheet1',lambda:Sheet(10,10,URL('callback')),0)
    #sheet.cell('r0c3',value='=r0c0+r0c1+r0c2',readonly=True)
    return dict(sheet=sheet)

