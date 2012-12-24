import re
import urllib
import urllib2
from BeautifulSoup import BeautifulSoup

page = urllib2.urlopen('http://www.telegraph.co.uk/technology/internet/9524681/Sir-Tim-Berners-Lee-accuses-government-of-draconian-internet-snooping.html')
soup = BeautifulSoup(page)

items = soup.findAll(['h1','h2','h3','h4','h5','h6','p'])
text =  '\n'.join(''.join(item.findAll(text=True)) for item in items).encode('utf8')
text = re.sub('\s*\n\s*','\n',re.sub('[ \t]+',' ',text))
print text
