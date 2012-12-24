import re

regex_url = re.compile(r'''                                                     
     (^(                                  # (/a/c/f.e/s)                        
         /(?P<a> [\w\s+]+ )               # /a=app                              
         (                                # (/c.f.e/s)                          
             /(?P<c> [\w\s+]+ )           # /a/c=controller                     
             (                            # (/f.e/s)                            
                 /(?P<f> [\w\s+]+ )       # /a/c/f=function                     
                 (                        # (.e)                                
                     \.(?P<e> [\w\s+]+ )  # /a/c/f.e=extension                  
                 )?                                                             
                 (                        # (/s)                                
                     /(?P<r>              # /a/c/f.e/r=raw_args                 
                     .*                                                         
                     )                                                          
                 )?                                                             
             )?                                                                 
         )?                                                                     
     )?                                                                         
     /?$)                                                                       
     ''', re.X)

import time
n=100000
path = '/app/static/f.e/filename'
t0=time.time()
for k in range(n):
    m = regex_url.match(path)
    m.group('a')
    m.group('c')
    m.group('f')
print (time.time()-t0)/n

t0=time.time()
for k in range(n):
    m = path.split('/')
    lm = len(m)
    if lm==0: m.append('a')
    if lm==1: m.append('c')
    if lm==2: m.append('f')
print (time.time()-t0)/n
