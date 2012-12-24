db=DAL()

db.define_table("article",
        Field("title"),
        Field("slug"),
        Field("number_of_views", "integer", default=0)
    )
def printer(row):
    print row
    return True
db.article.slug.compute = lambda row: printer(row) and IS_SLUG()(row.title)[0]


article_id = db.article.insert(title='This is a Test')
row = db.article[article_id]
print 'xxx1'
print row.update_record(number_of_views=row.number_of_views + 1)  
print row.update_record(number_of_views=row.number_of_views + 1)  
print row.update_record(number_of_views=row.number_of_views + 1)  
print 'xxx2'
print row
