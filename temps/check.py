import re, sys

regex = re.compile('\w+\.\w+')

for line in open(sys.argv[1]).read().split(' def '):
    function = line.split('(',1)[0]
    links = regex.findall(line)
    m = {}
    for link in links: m[link]=m.get(link,0)+1
    print function
    for link, count in sorted([(v,k) for v,k in m.iteritems()]):
        if count>1:
            print '    ',link, count
    

    
