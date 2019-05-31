#!/bin/bash

# This script will install web2py with nginx+uwsgi on centos 7
# This script is based on excellent tutorial by Justin Ellingwood on 
# https://www.digitalocean.com/community/tutorials/how-to-deploy-web2py-python-applications-with-uwsgi-and-nginx-on-centos-7

#
# Phase 1: First, let's ask a few things
#

read -p "Enter username under which web2py will be installed [web2py]: " USERNAME
USERNAME=${USERNAME:-web2py}

read -p "Enter path where web2py will be installed [/opt/web2py_apps]: " WEB2PY_PATH
WEB2PY_PATH=${WEB2PY_PATH:-/opt/web2py_apps}

read -p "Web2py subdirectory will be called: [web2py]: " WEB2PY_APP
WEB2PY_APP=${WEB2PY_APP:-web2py}

read -p "Enter your web2py admin password: " WEB2PY_PASS

read -p "Enter your domain name: " YOUR_SERVER_DOMAIN

#  open new user
useradd -d $WEB2PY_PATH $USERNAME

# if it's not already open, let's create a directory for web2py
mkdir -p $WEB2PY_PATH

# now let's create a self signed certificate
cd $WEB2PY_PATH

openssl req -x509 -new -newkey rsa:4096 -days 3652 -nodes -keyout $WEB2PY_APP.key -out $WEB2PY_APP.crt

#
# phase 2: That was all the input that we needed so let's install the components
#

echo "Installing necessary components"

# Verify packages are up to date
yum -y upgrade

# Install required packages
yum install -y epel-release
yum install -y python-devel python-pip gcc nginx wget unzip python-psycopg2 MySQL-python

# download and unzip web2py

echo "Downloading web2py"

cd $WEB2PY_PATH
wget http://web2py.com/examples/static/web2py_src.zip
unzip web2py_src.zip
rm web2py_src.zip

# preparing wsgihandler
chown -R $USERNAME.$USERNAME $WEB2PY_PATH/$WEB2PY_APP
mv $WEB2PY_PATH/$WEB2PY_APP/handlers/wsgihandler.py $WEB2PY_PATH/$WEB2PY_APP

# now let's install uwsgi

pip install uwsgi

# preparing directories
mkdir -p /etc/uwsgi/sites
mkdir -p /var/log/uwsgi
mkdir -p /etc/nginx/ssl/

#
#  Phase 3: Ok, everything is installed now so we'll configure things
#

# Create configuration file for uwsgi in /etc/uwsgi/$WEB2PY_APP.ini
echo '[uwsgi]
chdir = WEB2PY_PATH_PLACEHOLDER/WEB2PY_APP_PLACEHOLDER
module = wsgihandler:application

master = true
processes = 5

uid = USERNAME_PLACEHOLDER
socket = /run/uwsgi/WEB2PY_APP_PLACEHOLDER.sock
chown-socket = USERNAME_PLACEHOLDER:nginx
chmod-socket = 660
vacuum = true
' >/etc/uwsgi/sites/$WEB2PY_APP.ini

sed -i "s@WEB2PY_PATH_PLACEHOLDER@$WEB2PY_PATH@" /etc/uwsgi/sites/$WEB2PY_APP.ini
sed -i "s@WEB2PY_APP_PLACEHOLDER@$WEB2PY_APP@" /etc/uwsgi/sites/$WEB2PY_APP.ini
sed -i "s@USERNAME_PLACEHOLDER@$USERNAME@" /etc/uwsgi/sites/$WEB2PY_APP.ini

# Create a daemon configuration file for uwsgi
cat  > /etc/systemd/system/uwsgi.service <<EOF
[Unit]
Description=uWSGI Emperor service

[Service]
ExecStartPre=/usr/bin/bash -c 'mkdir -p /run/uwsgi; chown USERNAME_PLACEHOLDER:nginx /run/uwsgi'
ExecStart=/usr/bin/uwsgi --emperor /etc/uwsgi/sites
Restart=always
KillSignal=SIGQUIT
Type=notify
NotifyAccess=all

[Install]
WantedBy=multi-user.target
EOF

sed -i "s@USERNAME_PLACEHOLDER@$USERNAME@" /etc/systemd/system/uwsgi.service

#chmod 777 /etc/systemd/system/uwsgi.service

# create a nginx configuration file
cat  > /etc/nginx/nginx.conf <<EOF
# For more information on configuration, see:
#   * Official English Documentation: http://nginx.org/en/docs/
#   * Official Russian Documentation: http://nginx.org/ru/docs/

user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    log_format  main  '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                      '\$status \$body_bytes_sent "\$http_referer" '
                      '"\$http_user_agent" "\$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;

    sendfile            on;
    tcp_nopush          on;
    tcp_nodelay         on;
    keepalive_timeout   65;
    types_hash_max_size 2048;

    include             /etc/nginx/mime.types;
    default_type        application/octet-stream;

    # Load modular configuration files from the /etc/nginx/conf.d directory.
    # See http://nginx.org/en/docs/ngx_core_module.html#include
    # for more information.
    include /etc/nginx/conf.d/*.conf;

    server {
        listen       80 default_server;
        listen       [::]:80 default_server;
        server_name  YOUR_SERVER_DOMAIN_PLACEHOLDER;
        root         /usr/share/nginx/html;

        # Load configuration files for the default server block.
        include /etc/nginx/default.d/*.conf;

        location ~* /(\w+)/static/ {
            root WEB2PY_PATH_PLACEHOLDER/WEB2PY_APP_PLACEHOLDER/applications/;
        }

        location / {
            include uwsgi_params;
            uwsgi_pass unix:/run/uwsgi/WEB2PY_APP_PLACEHOLDER.sock;
        }

        error_page 404 /404.html;
            location = /40x.html {
        }

        error_page 500 502 503 504 /50x.html;
            location = /50x.html {
        }
    }
    
    server {
        listen 443;
        server_name YOUR_SERVER_DOMAIN_PLACEHOLDER;
        
        ssl on;
        ssl_certificate /etc/nginx/ssl/WEB2PY_APP_PLACEHOLDER.crt;
        ssl_certificate_key /etc/nginx/ssl/WEB2PY_APP_PLACEHOLDER.key;
        
        ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
        ssl_ciphers "HIGH:!aNULL:!MD5 or HIGH:!aNULL:!MD5:!3DES";
        ssl_prefer_server_ciphers on;
        
        location / {
            include uwsgi_params;
            uwsgi_pass unix:/run/uwsgi/WEB2PY_APP_PLACEHOLDER.sock;
        }
    }
}
EOF

sed -i "s@YOUR_SERVER_DOMAIN_PLACEHOLDER@$YOUR_SERVER_DOMAIN@" /etc/nginx/nginx.conf
sed -i "s@WEB2PY_PATH_PLACEHOLDER@$WEB2PY_PATH@" /etc/nginx/nginx.conf
sed -i "s@WEB2PY_APP_PLACEHOLDER@$WEB2PY_APP@" /etc/nginx/nginx.conf

#
# Phase 4: everything is configured now, just a few final touches
#

# copying certificates to nginx directory
mv $WEB2PY_PATH/$WEB2PY_APP.crt* /etc/nginx/ssl
mv $WEB2PY_PATH/$WEB2PY_APP.key* /etc/nginx/ssl

# creating web2py admin password
cd $WEB2PY_PATH/$WEB2PY_APP
python -c "from gluon.main import save_password; save_password('$WEB2PY_PASS',443)"
chown -R $USERNAME.$USERNAME $WEB2PY_PATH/$WEB2PY_APP

# taking care of permissions
chmod 700 /etc/nginx/ssl
usermod -a -G $USERNAME nginx
chmod 710 $WEB2PY_PATH

# enabling daemons
systemctl start nginx
systemctl start uwsgi
systemctl enable nginx
systemctl enable uwsgi

# If firewall is active make sure these ports are open

firewall-cmd --zone=public --add-port=80/tcp --permanent
firewall-cmd --zone=public --add-port=443/tcp --permanent
firewall-cmd --zone=public --add-port=22/tcp --permanent
firewall-cmd --reload

echo
echo 'Web2py is now installed on this server!'
echo

