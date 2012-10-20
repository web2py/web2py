def variables():
    return dict(a=10, b=20)


def test_for():
    return dict()


def test_if():
    return dict()


def test_try():
    return dict()


def test_def():
    return dict()


def escape():
    return dict(message='<h1>text is scaped</h1>')


def xml():
    return dict(message=XML('<h1>text is not escaped</h1>'))


def beautify():
    return dict(message=BEAUTIFY(request))
