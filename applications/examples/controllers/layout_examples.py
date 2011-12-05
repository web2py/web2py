def civilized():
    response.menu = [['civilized', True, URL('civilized'
                     )], ['slick', False, URL('slick')],
                     ['basic', False, URL('basic')]]
    response.flash = 'you clicked on civilized'
    return dict(message='you clicked on civilized')


def slick():
    response.menu = [['civilized', False, URL('civilized'
                     )], ['slick', True, URL('slick')],
                     ['basic', False, URL('basic')]]
    response.flash = 'you clicked on slick'
    return dict(message='you clicked on slick')


def basic():
    response.menu = [['civilized', False, URL('civilized'
                     )], ['slick', False, URL('slick')],
                     ['basic', True, URL('basic')]]
    response.flash = 'you clicked on basic'
    return dict(message='you clicked on basic')



