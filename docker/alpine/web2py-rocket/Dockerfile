FROM alpine:latest

#LABEL your_label

RUN apk add --no-cache python py-pip py-setuptools unzip wget && \
 pip install --upgrade pip && \
 pip install virtualenv 

RUN addgroup -S web2py && \
 adduser -D -S -G web2py web2py

USER web2py

RUN virtualenv /home/web2py && \
 rm -rf /home/web2py/web2py && \
 cd /home/web2py/ && \
 rm -f web2py_src.zip && \
 wget -c http://web2py.com/examples/static/web2py_src.zip && \
 unzip -o web2py_src.zip && \
 rm -rf /home/web2py/web2py/applications/examples && \
 chmod 755 -R /home/web2py/web2py

WORKDIR /home/web2py/web2py

EXPOSE 8000

CMD . /home/web2py/bin/activate && python /home/web2py/web2py/web2py.py --nogui --no-banner -a 'a' -i 0.0.0.0 -p 8000
