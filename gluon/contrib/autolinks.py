import re, cgi, sys
from simplejson import loads
import BeautifulSoup
import urllib

MAPS = [
    (re.compile('http://\S*?flickr.com/\S*'),
     'http://www.flickr.com/services/oembed/'),
    (re.compile('http://\S*.youtu(\.be|be\.com)/watch\S*'),
     'http://www.youtube.com/oembed'),
    (re.compile('http://www.hulu.com/watch/\S*'),
     'http://www.hulu.com/api/oembed.json'),
    (re.compile('http://vimeo.com/\S*'),
     'http://vimeo.com/api/oembed.json'),
    (re.compile('http://www.slideshare.net/[^\/]+/\S*'), 
     'http://www.slideshare.net/api/oembed/2'),
    (re.compile('http://qik.com/\S*'),
     'http://qik.com/api/oembed.json'),
    (re.compile('http://www.polleverywhere.com/\w+/\S+'),
     'http://www.polleverywhere.com/services/oembed/'),
    (re.compile('http://www.slideshare.net/\w+/\S+'),
     'http://www.slideshare.net/api/oembed/2'),
    (re.compile('http://\S+.wordpress.com/\S+'),
     'http://public-api.wordpress.com/oembed/'),
    (re.compile('http://*.revision3.com/\S+'),
     'http://revision3.com/api/oembed/'),
    (re.compile('http://www.slideshare.net/\w+/\S+'),
     'http://api.smugmug.com/services/oembed/'),
    (re.compile('http://\S+.viddler.com/\S+'),
     'http://lab.viddler.com/services/oembed/'),
    ]

regex_link = re.compile('https?://\S+')

def oembed(url):
    for k,v in MAPS:
        if k.match(url):
            oembed = v+'?format=json&url='+cgi.escape(url)
            try:
                return loads(urllib.urlopen(oembed).read())
            except: pass
    return {}

def expand_one(url,cdict):
    if cdict and url in cdict:
        r = cdict[url]
    elif cdict:
        r = cdict[url] = oembed(url)
    else:
        r = oembed(url)
    if 'html' in r:
        return '<embed>%s</embed>' % r['html']
    return '<a href="%(u)s">%(u)s</a>' % dict(u=url)

def expand_all(html,cdict=None):
    soup = BeautifulSoup.BeautifulSoup(html)
    for txt in soup.findAll(text=True):
        if txt.parent.name != 'a':
            ntxt = regex_link.sub(
                lambda match: expand_one(match.group(0),cdict), txt)
            txt.replaceWith(ntxt)
    return str(soup)


def test():
    example="""
<h3>Fringilla nisi parturient nullam</h3>
<p>http://www.youtube.com/watch?v=IWBFiI5RrA0</p>
<p>Elementum sodales est varius magna leo sociis erat. Nascetur pretium non
ultricies gravida. Condimentum at nascetur tempus. Porttitor viverra ipsum
accumsan neque aliquet. Ultrices vestibulum tempor quisque eget sem eget.
Ornare malesuada tempus dolor dolor magna consectetur. Nisl dui non curabitur
laoreet tortor.</p>
"""
    return expand_all(example)


if __name__=="__main__":
    if len(sys.argv)>1:
        print expand_all(open(sys.argv[1]).read())
    else:
        print test()
