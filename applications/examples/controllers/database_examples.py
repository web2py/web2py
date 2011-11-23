from gluon.fileutils import read_file

response.menu = [['Register User', False, URL(r=request,
                 f='register_user')], ['Register Dog', False,
                 URL('register_dog')], ['Register Product'
                 , False, URL('register_product')],
                 ['Buy product', False, URL('buy')]]


def register_user():
    """ simple user registration form with validation and database.insert()
        also lists all records currently in the table"""

    # ## create an insert form from the table

    form = SQLFORM(db.users)

    # ## if form correct perform the insert

    if form.accepts(request.vars, session):
        response.flash = 'new record inserted'

    # ## and get a list of all users

    records = SQLTABLE(db().select(db.users.ALL))
    return dict(form=form, records=records)


def register_dog():
    """ simple user registration form with validation and database.insert()
        also lists all records currently in the table"""

    form = SQLFORM(db.dogs)
    if form.accepts(request.vars, session):
        response.flash = 'new record inserted'
    download = URL('download')  # to see the picture
    records = SQLTABLE(db().select(db.dogs.ALL), upload=download)
    return dict(form=form, records=records)


def register_product():
    """ simple user registration form with validation and database.insert()
        also lists all records currently in the table"""

    form = SQLFORM(db.products)
    if form.accepts(request.vars, session):
        response.flash = 'new record inserted'
    records = SQLTABLE(db().select(db.products.ALL))
    return dict(form=form, records=records)


def buy():
    """ uses a form to query who is buying what. validates form and
        updates existing record or inserts new record in purchases """

    buyerRecords = db().select(db.users.ALL)
    buyerOptions = []
    for row in buyerRecords:
        buyerOptions.append(OPTION(row.name, _value=row.id))

    productRecords = db().select(db.products.ALL)
    productOptions = []
    for row in productRecords:
        productOptions.append(OPTION(row.name, _value=row.id))

    form = FORM(TABLE(
                TR('Buyer id:',
                    SELECT(buyerOptions,_name='buyer_id')),
                TR('Product id:',
                    SELECT(productOptions,_name='product_id')),
                TR('Quantity:',
                    INPUT(_type='text', _name='quantity',
                          requires=IS_INT_IN_RANGE(1, 100))),
                TR('',
                    INPUT(_type='submit', _value='Order'))
                ))
    if form.accepts(request.vars, session, keepvalues=True):

        # ## check if user is in the database

        if len(db(db.users.id == form.vars.buyer_id).select()) == 0:
            form.errors.buyer_id = 'buyer not in database'

        # ## check if product is the database

        if len(db(db.products.id == form.vars.product_id).select())\
             == 0:
            form.errors.product_id = 'product not in database'

        # ## if no errors

        if len(form.errors) == 0:

            # ## get a list of same purchases by same user

            purchases = db((db.purchases.buyer_id == form.vars.buyer_id)
                            & (db.purchases.product_id
                            == form.vars.product_id)).select()

            # ## if list contains a record, update that record

            if len(purchases) > 0:
                purchases[0].update_record(quantity=purchases[0].quantity
                         + form.vars.quantity)
            else:

            # ## or insert a new record in table
                db.purchases.insert(buyer_id=form.vars.buyer_id,
                                    product_id=form.vars.product_id,
                                    quantity=form.vars.quantity)
            response.flash = 'product purchased!'
    if len(form.errors):
        response.flash = 'invalid values in form!'

    # ## now get a list of all purchases

    # quick fix to make it runnable on gae
    if purchased:
        records = db(purchased).select(db.users.name,
                                       db.purchases.quantity,
                                       db.products.name)
    else:
        records = db().select(db.purchases.ALL)
    return dict(form=form, records=SQLTABLE(records), vars=form.vars,
                vars2=request.vars)


def delete_purchased():
    """ delete all records in purchases """

    db(db.purchases.id > 0).delete()
    redirect(URL('buy'))


def reset_purchased():
    """ set quantity=0 for all records in purchases """

    db(db.purchases.id > 0).update(quantity=0)
    redirect(URL('buy'))


def download():
    """ used to download uploaded files """

    import gluon.contenttype
    app = request.application
    filename = request.args[0]
    response.headers['Content-Type'] = \
        gluon.contenttype.contenttype(filename)
    return read_file('applications/%s/uploads/%s' % (app, filename), 'rb')


