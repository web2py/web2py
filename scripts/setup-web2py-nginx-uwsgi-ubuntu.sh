echo 'setup-web2py-nginx-uwsgi-ubuntu-precise.sh'
echo 'Requires Ubuntu 12.04 and installs Nginx + uWSGI + Web2py'

# Get Web2py Admin Password
echo -e "Web2py Admin Password: \c "
read  PW
# Upgrade and install needed software
apt-get update
apt-get -y upgrade
apt-get -y dist-upgrade
apt-get autoremove
apt-get autoclean
apt-get -y install nginx-full
apt-get -y install build-essential python-dev libxml2-dev python-pip
pip install --upgrade pip
pip install --upgrade uwsgi
# Create configuration file /etc/nginx/sites-available/web2py
echo 'server {
        listen          80;
        server_name     $hostname;
        #to enable correct use of response.static_version
        #location ~* /(\w+)/static(?:/_[\d]+\.[\d]+\.[\d]+)?/(.*)$ {
        #    alias /home/www-data/web2py/applications/$1/static/$2;
        #    expires max;
        #}
        location ~* /(\w+)/static/ {
            root /home/www-data/web2py/applications/;
            #remove next comment on production
            #expires max;
        }
        location / {
            #uwsgi_pass      127.0.0.1:9001;
            uwsgi_pass      unix:///tmp/web2py.socket;
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
            #uwsgi_pass      127.0.0.1:9001;
            uwsgi_pass      unix:///tmp/web2py.socket;
            include         uwsgi_params;
            uwsgi_param     UWSGI_SCHEME $scheme;
            uwsgi_param     SERVER_SOFTWARE    nginx/$nginx_version;
        }

}' >/etc/nginx/sites-available/web2py

ln -s /etc/nginx/sites-available/web2py /etc/nginx/sites-enabled/web2py
rm /etc/nginx/sites-enabled/default
mkdir /etc/nginx/ssl
cd /etc/nginx/ssl
openssl genrsa -out web2py.key 1024
openssl req -batch -new -key web2py.key -out web2py.csr
openssl x509 -req -days 1780 -in web2py.csr -signkey web2py.key -out web2py.crt

# Prepare folders for uwsgi
sudo mkdir /etc/uwsgi
sudo mkdir /var/log/uwsgi

# Create configuration file /etc/uwsgi/web2py.xml
echo '<uwsgi>
    <socket>/tmp/web2py.socket</socket>
    <pythonpath>/home/www-data/web2py/</pythonpath>
    <mount>/=wsgihandler:application</mount>
    <master/>
    <processes>4</processes>
    <harakiri>60</harakiri>
    <reload-mercy>8</reload-mercy>
    <cpu-affinity>1</cpu-affinity>
    <stats>/tmp/stats.socket</stats>
    <max-requests>2000</max-requests>
    <limit-as>512</limit-as>
    <reload-on-as>256</reload-on-as>
    <reload-on-rss>192</reload-on-rss>
    <uid>www-data</uid>
    <gid>www-data</gid>
    <cron>0 0 -1 -1 -1 python /home/www-data/web2py/web2py.py -Q -S welcome -M -R scripts/sessions2trash.py -A -o</cron>
    <no-orphans/>
</uwsgi>' >/etc/uwsgi/web2py.xml

#Create a configuration file for uwsgi in emperor-mode
#for Upstart in /etc/init/uwsgi-emperor.conf
echo '# Emperor uWSGI script

description "uWSGI Emperor"
start on runlevel [2345]
stop on runlevel [06]
##
#remove the comments in the next section to enable static file compression for the welcome app
#in that case, turn on gzip_static on; on /etc/nginx/nginx.conf
##
#pre-start script
#    python /home/www-data/web2py/web2py.py -S welcome -R scripts/zip_static_files.py
#    chown -R www-data:www-data /home/www-data/web2py/*
#end script
respawn
exec uwsgi --master --die-on-term --emperor /etc/uwsgi --logto /var/log/uwsgi/uwsgi.log
' > /etc/init/uwsgi-emperor.conf
# Install Web2py
apt-get -y install unzip
mkdir /home/www-data
cd /home/www-data
wget http://web2py.com/examples/static/web2py_src.zip
unzip web2py_src.zip
rm web2py_src.zip
# Download latest version of sessions2trash.py
wget http://web2py.googlecode.com/hg/scripts/sessions2trash.py -O /home/www-data/web2py/scripts/sessions2trash.py
chown -R www-data:www-data web2py
cd /home/www-data/web2py
sudo -u www-data python -c "from gluon.main import save_password; save_password('$PW',443)"
start uwsgi-emperor
/etc/init.d/nginx restart

## you can reload uwsgi with
# restart uwsgi-emperor
## and stop it with
# stop uwsgi-emperor
## to reload web2py only (without restarting uwsgi)
# touch /etc/uwsgi/web2py.xml

