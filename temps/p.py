from gluon.contrib.populate import populate
populate(db.auth_user,10)
print db(db.auth_user).select()
