from gluon import XML

def button(merchant_id="123456789012345",
           products=[dict(name="shoes",
                          quantity=1,
                          price=23.5,
                          currency='USD',
                          description="running shoes black")]):
    t = '<input name="item_%(key)s_%(k)s" type="hidden" value="%(value)s"/>'
    list_products = ''
    for k,product in enumerate(products):
        for key,value in product.items():
            list_products += t % dict(k=k+1,key=key,value=value)
    button = '<form action="https://checkout.google.com/api/checkout/v2/checkoutForm/Merchant/%s" id="BB_BuyButtonForm" method="post" name="BB_BuyButtonForm" target="_top">%s<input name="_charset_" type="hidden" value="utf-8"/><input alt="" src="https://checkout.google.com/buttons/buy.gif?merchant_id=%s&amp;w=117&amp;h=48&amp;style=white&amp;variant=text&amp;loc=en_US" type="image"/></form>' % (merchant_id, list_products, merchant_id)
    return XML(button)







