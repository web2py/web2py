#!/bin/bash

echo 'setup-web2py-nginx-uwsgi-ubuntu.sh'
echo 'Requires Ubuntu 10.04 (LTS) and installs Nginx + uWSGI + Web2py'

# Get Web2py Admin Password
echo -e "Web2py Admin Password: \c "
read  PW

# Upgrade and install needed software
apt-get update
apt-get -y upgrade
apt-get install python-software-properties
add-apt-repository ppa:nginx/stable
add-apt-repository  ppa:uwsgi/release
apt-get update
apt-get -y install nginx-full
apt-get -y install uwsgi-python

# Create configuration file /etc/nginx/sites-available/web2py
echo 'server {
        listen          80;
        server_name     $hostname;
        location ~* /(\w+)/static/ {
           root /home/www-data/web2py/applications/;
        }
         location / {
                uwsgi_pass      127.0.0.1:9001;
                include         uwsgi_params;
                uwsgi_param     UWSGI_SCHEME $scheme;
                uwsgi_param     SERVER_SOFTWARE    nginx/$nginx_version;
        }
}

server {
        listen          443;
        server_name     $hostname;
        ssl                     on;
        ssl_certificate         /etc/nginx/ssl/web2py.crt;
        ssl_certificate_key     /etc/nginx/ssl/web2py.key;
        location / {
                uwsgi_pass      127.0.0.1:9001;
                include         uwsgi_params;
                uwsgi_param     UWSGI_SCHEME $scheme;
                uwsgi_param     SERVER_SOFTWARE    nginx/$nginx_version;
        }

}' >/etc/nginx/sites-available/web2py

ln -s /etc/nginx/sites-available/web2py /etc/nginx/sites-enabled/web2py
rm /etc/nginx/sites-enabled/default
rm /etc/nginx/sites-available/default
mkdir /etc/nginx/ssl
cd /etc/nginx/ssl
openssl genrsa -out web2py.key 1024
openssl req -batch -new -key web2py.key -out web2py.csr
openssl x509 -req -days 1780 -in web2py.csr -signkey web2py.key -out web2py.crt

# Create configuration file /etc/uwsgi-python/apps-available/web2py.xml
echo '<uwsgi>
    <socket>127.0.0.1:9001</socket>
    <pythonpath>/home/www-data/web2py/</pythonpath>
    <app mountpoint="/">
        <script>wsgihandler</script>
    </app>
</uwsgi>' >/etc/uwsgi-python/apps-available/web2py.xml
ln -s /etc/uwsgi-python/apps-available/web2py.xml /etc/uwsgi-python/apps-enabled/web2py.xml

# Install Web2py
apt-get -y install unzip
cd /home
mkdir www-data
cd www-data
wget http://web2py.com/examples/static/web2py_src.zip
unzip web2py_src.zip
rm web2py_src.zip
chown -R www-data:www-data web2py
cd /home/www-data/web2py
sudo -u www-data python -c "from gluon.main import save_password; save_password('$PW',443)"
/etc/init.d/uwsgi-python restart
/etc/init.d/nginx restart
