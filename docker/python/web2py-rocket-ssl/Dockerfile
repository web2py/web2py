FROM python:2.7

#LABEL your_label

RUN apt update && \
 apt install -y unzip wget

RUN wget -c http://web2py.com/examples/static/web2py_src.zip && \
 unzip -o web2py_src.zip && \
 rm -rf /web2py/applications/examples && \
 cd /web2py && \
 openssl genrsa 1024 > web2py.key && chmod 400 web2py.key && \
 openssl req -new -x509 -nodes -sha1 -days 1780 -subj '/C=ID/ST=Jakarta/L=Jakarta/O=stifix/OU=IT/CN=stifix.com' -key web2py.key > web2py.crt && \
 openssl x509 -noout -fingerprint -text < web2py.crt > web2py.info && \
 chmod 755 -R /web2py

WORKDIR /web2py

EXPOSE 443

CMD python /web2py/web2py.py --nogui --no-banner -a 'a' -c web2py.crt -k web2py.key -i 0.0.0.0 -p 443
