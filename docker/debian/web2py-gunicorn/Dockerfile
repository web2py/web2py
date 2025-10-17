FROM debian:latest

#LABEL your_label

RUN apt update && \
 apt install -y python3 python3-setuptools unzip wget virtualenv
 
RUN groupadd -r web2py && \
 useradd -m -r -g web2py web2py

USER web2py

RUN virtualenv /home/web2py && \
 rm -rf /home/web2py/web2py && \
 cd /home/web2py/ && \
 rm -f web2py_src.zip && \
 wget -c http://web2py.com/examples/static/web2py_src.zip && \
 unzip -o web2py_src.zip && \
 rm -rf /home/web2py/web2py/applications/examples && \
 chmod 755 -R /home/web2py/web2py

RUN /home/web2py/bin/bin/pip3 install gunicorn
RUN /home/web2py/bin/bin/pip3 install legacy-cgi

WORKDIR /home/web2py/web2py

EXPOSE 8000

CMD . /home/web2py/bin/activate && python3 /home/web2py/web2py/anyserver.py -s gunicorn -i 0.0.0.0 -p 8000
