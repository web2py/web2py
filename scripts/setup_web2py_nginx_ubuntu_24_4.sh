#!/bin/bash
echo 'setup-web2py-nginx-uwsgi-ubuntu-24.04.sh'
echo 'Requires Ubuntu 24.04 and installs Nginx + uWSGI + Web2py (using Python venv)'

if [[ $EUID -ne 0 ]]; then
   echo "You must run the script as root or using sudo"
   exit 1
fi

# Parse command line arguments
nopassword=0
nocertificate=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --no-password) nopassword=1; shift 1;;
    --no-certificate) nocertificate=1; shift 1;;
  esac
done

# Get Web2py Admin Password
if [ "$nopassword" -eq 0 ]; then
  echo -e "Web2py Admin Password: \c "
  read -s PW
  printf "\n"
fi

# Upgrade and install needed software
apt-get update
apt-get -y upgrade
apt-get autoremove
apt-get autoclean
apt-get -y install nginx-full python3-venv build-essential python3-dev libxml2-dev unzip

# Create and activate a Python virtualenv for web2py and uWSGI
VENV_PATH="/home/www-data/web2py-venv"
mkdir -p /home/www-data
python3 -m venv $VENV_PATH
chown -R www-data:www-data $VENV_PATH

# Activate venv and install pip dependencies
sudo -u www-data bash <<EOF
source $VENV_PATH/bin/activate
pip install --upgrade pip setuptools
pip install uwsgi
EOF

# Create common nginx sections
mkdir -p /etc/nginx/conf.d/web2py
cat >/etc/nginx/conf.d/web2py/gzip_static.conf <<'EOGZIPSTATIC'
gzip_static on;
gzip_http_version   1.1;
gzip_proxied        expired no-cache no-store private auth;
gzip_disable        "MSIE [1-6]\.";
gzip_vary           on;
EOGZIPSTATIC

cat >/etc/nginx/conf.d/web2py/gzip.conf <<'EOGZIP'
gzip on;
gzip_disable "msie6";
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_buffers 16 8k;
gzip_http_version 1.1;
gzip_types text/plain text/css application/json application/x-javascript text/xml application/xml application/xml+rss text/javascript;
EOGZIP

# Create configuration file /etc/nginx/sites-available/web2py
cat >/etc/nginx/sites-available/web2py <<'EONGINX'
server {
        listen          80;
        server_name     $hostname;
        location ~* ^/(\w+)/static(?:/_[\d]+\.[\d]+\.[\d]+)?/(.*)$ {
            alias /home/www-data/web2py/applications/$1/static/$2;
            expires max;
        }
        location / {
            uwsgi_pass      unix:///tmp/web2py.socket;
            include         uwsgi_params;
            uwsgi_param     UWSGI_SCHEME $scheme;
            uwsgi_param     SERVER_SOFTWARE    nginx/$nginx_version;
        }
}
server {
        listen 443 default_server ssl;
        server_name     $hostname;
        ssl_certificate         /etc/nginx/ssl/web2py.crt;
        ssl_certificate_key     /etc/nginx/ssl/web2py.key;
        ssl_prefer_server_ciphers on;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;
        ssl_ciphers ECDHE-RSA-AES256-SHA:DHE-RSA-AES256-SHA:DHE-DSS-AES256-SHA:DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA;
        ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
        keepalive_timeout    70;
        location / {
            uwsgi_pass      unix:///tmp/web2py.socket;
            include         uwsgi_params;
            uwsgi_param     UWSGI_SCHEME $scheme;
            uwsgi_param     SERVER_SOFTWARE    nginx/$nginx_version;
        }
        location ~* ^/(\w+)/static(?:/_[\d]+\.[\d]+\.[\d]+)?/(.*)$ {
            alias /home/www-data/web2py/applications/$1/static/$2;
            expires max;
        }
}
EONGINX

ln -sf /etc/nginx/sites-available/web2py /etc/nginx/sites-enabled/web2py
rm -f /etc/nginx/sites-enabled/default
mkdir -p /etc/nginx/ssl
cd /etc/nginx/ssl
if [ "$nocertificate" -eq 0 ]; then
    openssl req -x509 -nodes -sha256 -days 365 -newkey rsa:2048 -keyout web2py.key -out web2py.crt
    openssl x509 -noout -text -in web2py.crt -out web2py.info
fi

# Prepare folders for uwsgi
mkdir -p /etc/uwsgi
mkdir -p /var/log/uwsgi
mkdir -p /etc/systemd/system

# uWSGI Emperor systemd service using the virtualenv's uwsgi
cat >/etc/systemd/system/emperor.uwsgi.service <<EOF
[Unit]
Description = uWSGI Emperor
After = syslog.target

[Service]
ExecStart = $VENV_PATH/bin/uwsgi --master --die-on-term --emperor /etc/uwsgi --logto /var/log/uwsgi/uwsgi.log
RuntimeDirectory = uwsgi
Restart = always
KillSignal = SIGQUIT
Type = notify
StandardError = syslog
NotifyAccess = all
User = www-data
Group = www-data

[Install]
WantedBy = multi-user.target
EOF

# Create configuration file /etc/uwsgi/web2py.ini
cat >/etc/uwsgi/web2py.ini <<EOF
[uwsgi]
socket = /tmp/web2py.socket
pythonpath = /home/www-data/web2py/
mount = /=wsgihandler:application
processes = 4
master = true
harakiri = 60
reload-mercy = 8
cpu-affinity = 1
stats = /tmp/stats.socket
max-requests = 2000
limit-as = 512
reload-on-as = 256
reload-on-rss = 192
uid = www-data
gid = www-data
touch-reload = /home/www-data/web2py/routes.py
cron = 0 0 -1 -1 -1 python3 /home/www-data/web2py/web2py.py -Q -S welcome -M -R scripts/sessions2trash.py -A -o
no-orphans = true
home = $VENV_PATH
EOF

# Install Web2py
cd /home/www-data
wget http://web2py.com/examples/static/web2py_src.zip

unzip web2py_src.zip
mv web2py/handlers/wsgihandler.py web2py/wsgihandler.py
rm web2py_src.zip
cd /home/www-data
chown -R www-data:www-data web2py
chown -R www-data:www-data /home/www-data
chmod -R 755 /home/www-data
cd /home/www-data/web2py

# Set the web2py admin password (note PYTHONPATH is provided!)
if [ "$nopassword" -eq 0 ]; then
   sudo -u www-data env PYTHONPATH=/home/www-data/web2py $VENV_PATH/bin/python3 -c "from gluon.main import save_password; save_password('$PW',443)"
fi
chown -R www-data:www-data /var/log/uwsgi
chmod 755 /var/log/uwsgi


systemctl daemon-reload
systemctl restart nginx
systemctl start emperor.uwsgi.service
systemctl enable emperor.uwsgi.service

cat <<EOFMSG

You can stop uwsgi and nginx with:

  sudo systemctl stop nginx
  sudo systemctl stop emperor.uwsgi.service

and start them with:

  sudo systemctl start nginx
  sudo systemctl start emperor.uwsgi.service

EOFMSG