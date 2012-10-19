def form():
    """ a simple entry form with various types of objects """

    form = FORM(TABLE(
        TR('Your name:', INPUT(_type='text', _name='name',
           requires=IS_NOT_EMPTY())),
        TR('Your email:', INPUT(_type='text', _name='email',
           requires=IS_EMAIL())),
        TR('Admin', INPUT(_type='checkbox', _name='admin')),
        TR('Sure?', SELECT('yes', 'no', _name='sure',
           requires=IS_IN_SET(['yes', 'no']))),
        TR('Profile', TEXTAREA(_name='profile',
           value='write something here')),
        TR('', INPUT(_type='submit', _value='SUBMIT')),
    ))
    if form.process().accepted:
        response.flash = 'form accepted'
    elif form.errors:
        response.flash = 'form is invalid'
    else:
        response.flash = 'please fill the form'
    return dict(form=form, vars=form.vars)
