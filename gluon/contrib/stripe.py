import urllib
import simplejson

class Stripe:
    """
    Usage:
    key='<api key>'
    d = Stripe(key).charge(
               amount=100,
               currency='usd',
               card_number='4242424242424242',
               card_exp_month='5',
               card_exp_year='2012',
               card_cvc_check='123',
               description='test charge')
    print d
    print Stripe(key).check(d['id'])
    print Stripe(key).refund(d['id'])
    Sample output (python dict):
    {u'fee': 0, u'description': u'test charge', u'created': 1321242072, u'refunded': False, u'livemode': False, u'object': u'charge', u'currency': u'usd', u'amount': 100, u'paid': True, u'id': u'ch_sdjasgfga83asf', u'card': {u'exp_month': 5, u'country': u'US', u'object': u'card', u'last4': u'4242', u'exp_year': 2012, u'type': u'Visa'}}

    if paid is True than transaction was processed
    """

    def __init__(self,key):
        self.key = key
    def charge(self,
               amount,
               currency='usd',
               card_number='4242424242424242',
               card_exp_month='5',
               card_exp_year='2012',
               card_cvc_check='123',
               description='test charge'):
        params = urllib.urlencode({'amount':amount,
                                   'currency':currency,
                                   'card[number]':card_number,
                                   'card[exp_month]':card_exp_month,
                                   'card[exp_year]':card_exp_year,
                                   'card[cvc_check]':card_cvc_check,
                                   'description':description})
        u = urllib.urlopen('https://%s:@api.stripe.com/v1/charges' % \
                               self.key,params)
        return simplejson.loads(u.read())

    def check(self,charge_id):
        u = urllib.urlopen('https://%s:@api.stripe.com/v1/charges/%s' % \
                               (self.key,charge_id))
        return simplejson.loads(u.read())

    def refund(self,charge_id):
        params = urllib.urlencode({})
        u = urllib.urlopen('https://%s:@api.stripe.com/v1/charges/%s/refund'%\
                               (self.key,charge_id),params)
        return simplejson.loads(u.read())

if __name__=='__main__':
    key = raw_input('user>')
    d=Stripe(key).charge(100)
    print 'charged',d['paid']
    s = Stripe(key).check(d[u'id'])
    print 'paid',s['paid'],s['amount'] ,s['currency']
    s = Stripe(key).refund(d[u'id'])
    print 'refunded',s['refunded']





