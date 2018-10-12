def test_index_exists(web2py):
    result = web2py.run('default', 'index', web2py)

    html = web2py.response.render('default/index/html', result)

    assert 'Welcome' in html
