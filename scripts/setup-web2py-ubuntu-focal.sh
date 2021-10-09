#!/bin/bash

# Check if user has root privileges
if [[ $EUID -ne 0 ]]; then
   echo "You must run the script as root or using sudo"
   exit 1
fi

echo "This script will:
1) install all modules need to run web2py on Ubuntu 20.04 with Python 3
2) install web2py in /home/www-data/
3) create a self signed ssl certificate
4) setup web2py with mod_wsgi
5) overwrite /etc/apache2/sites-available/default
6) restart apache.

You may want to read this script before running it.

Press a key to continue...[ctrl+C to abort]"

read CONFIRM

# parse command line arguments
nopassword=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --no-password) nopassword=1; shift 1;;
  esac
done
# Get Web2py Admin Password
if [ "$nopassword" -eq 0 ]
then
  echo -e "Web2py Admin Password: \c "
  read -s PW
  printf "\n"  # fix no new line artifact of "read -s" to avoid cleartext password
fi

echo "installing useful packages"
echo "=========================="
apt update
apt -y install ssh \
               zip \
               unzip \
               tar \
               build-essential \
               python3 \
               python3-dev \
               python3-psycopg2 \
               python3-matplotlib \
               python3-reportlab \
               ipython3 \
               postgresql \
               apache2 \
               libapache2-mod-wsgi-py3 \
               postfix \
               mercurial
/etc/init.d/postgresql restart

echo "downloading, installing and starting web2py"
echo "==========================================="
cd /home
mkdir www-data
cd www-data
rm web2py_src.zip*
wget http://web2py.com/examples/static/web2py_src.zip
unzip web2py_src.zip
mv web2py/handlers/wsgihandler.py web2py/wsgihandler.py
chown -R www-data:www-data web2py

echo "setting up apache modules"
echo "========================="
a2enmod \
    ssl \
    proxy \
    proxy_http \
    headers \
    expires \
    wsgi \
    rewrite

echo "creating a self signed certificate"
echo "=================================="
mkdir /etc/apache2/ssl
openssl genrsa 2048 > /etc/apache2/ssl/self_signed.key
chmod 400 /etc/apache2/ssl/self_signed.key
openssl req -new -x509 -nodes -sha1 -days 365 -subj "/C=US/ST=Utah/L=Lehi/O=Your Company, Inc./OU=IT/CN=yourdomain.com" -key /etc/apache2/ssl/self_signed.key > /etc/apache2/ssl/self_signed.cert
openssl x509 -noout -fingerprint -text < /etc/apache2/ssl/self_signed.cert > /etc/apache2/ssl/self_signed.info

echo "rewriting your apache config file to use mod_wsgi"
echo "================================================="
echo '
WSGIDaemonProcess web2py user=www-data group=www-data

<VirtualHost *:80>

 WSGIProcessGroup web2py
  WSGIScriptAlias / /home/www-data/web2py/wsgihandler.py
  WSGIPassAuthorization On

  <Directory /home/www-data/web2py>
    AllowOverride None
    Require all denied
    <Files wsgihandler.py>
      Require all granted
    </Files>
  </Directory>

  AliasMatch ^/([^/]+)/static/(?:_[\d]+.[\d]+.[\d]+/)?(.*) \
        /home/www-data/web2py/applications/$1/static/$2

  <Directory /home/www-data/web2py/applications/*/static/>
    Options -Indexes
    ExpiresActive On
    ExpiresDefault "access plus 1 hour"
    Require all granted
  </Directory>

  CustomLog /var/log/apache2/access.log common
  ErrorLog /var/log/apache2/error.log

</VirtualHost>

<VirtualHost *:443>
  SSLEngine on
  SSLCertificateFile /etc/apache2/ssl/self_signed.cert
  SSLCertificateKeyFile /etc/apache2/ssl/self_signed.key

  WSGIProcessGroup web2py
  WSGIScriptAlias / /home/www-data/web2py/wsgihandler.py
  WSGIPassAuthorization On

  <Directory /home/www-data/web2py>
    AllowOverride None
    Require all denied
    <Files wsgihandler.py>
      Require all granted
    </Files>
  </Directory>

  AliasMatch ^/([^/]+)/static/(?:_[\d]+.[\d]+.[\d]+/)?(.*) \
        /home/www-data/web2py/applications/$1/static/$2

  <Directory /home/www-data/web2py/applications/*/static/>
    Options -Indexes
    ExpiresActive On
    ExpiresDefault "access plus 1 hour"
    Require all granted
  </Directory>

  CustomLog /var/log/apache2/ssl-access.log common
  ErrorLog /var/log/apache2/error.log
</VirtualHost>
' > /etc/apache2/sites-available/default.conf  # FOR 14.04

sudo rm /etc/apache2/sites-enabled/*    # FOR 14.04
sudo a2ensite default                   # FOR 14.04


echo "restarting apache"
echo "================"

/etc/init.d/apache2 restart
cd /home/www-data/web2py

cd /home/www-data/web2py
if [ "$nopassword" -eq 0 ]
then
   sudo -u www-data python3 -c "from gluon.main import save_password; save_password('$PW',443)"
fi


echo ""
echo "Done!"
echo "==========================================="
