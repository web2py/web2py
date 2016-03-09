# Template helpers

import os


def A_button(*a, **b):
    b['_data-role'] = 'button'
    b['_data-inline'] = 'true'
    return A(*a, **b)

def button(href, label):
    if is_mobile:
        ret = A_button(SPAN(label), _href=href)
    else:
        ret = A(SPAN(label), _class='btn rounded', _href=href)
    return ret

def button_enable(href, app):
    if os.path.exists(os.path.join(apath(app, r=request), 'DISABLED')):
        text, classes = T("Enable"), "btn rounded red"
    else:
        text, classes = T("Disable"), "btn rounded gree"
    id = 'enable_' + app
    return A(text, _class=classes, _id=id, callback=href, target=id)

def sp_button(href, label):
    if request.user_agent().get('is_mobile'):
        ret = A_button(SPAN(label), _href=href)
    else:
        ret = A(SPAN(label), _class='btn pink rounded', _href=href)
    return ret

def helpicon():
    return IMG(_src=URL('static', 'images/help.png'), _alt='help')

