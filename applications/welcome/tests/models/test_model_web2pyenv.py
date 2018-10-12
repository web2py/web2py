def test_user_exists(web2py):
    db = web2py.db
    rows = db(db.auth_user.id > 0).select()
    assert len(rows) is 1
