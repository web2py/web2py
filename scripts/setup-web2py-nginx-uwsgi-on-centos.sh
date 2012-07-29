# Author: Peter Hutchinson
# License: BSD
#
# Installing Web2py with Nginx and Uwsgi on Centos 5 is really tricky. 
# There are lots of subtleties of ownership, and one has to take care 
# when installing python 2.6 not to stop the systems python2.4 from working. 
# Here is a script that does all the installation from a clean start machine. 
# The only thing that should need changing for another installation is 
# the $basearch (base architecture) of the machine. We assume:

basearch=i386

# This can be determined by doing 'uname -i'. 
# This is needed for the nginx installation.
# There is one script and three configuration files. 

# install development tools

yum install gcc gdbm-devel readline-devel ncurses-devel zlib-devel  bzip2-devel sqlite-devel db4-devel openssl-devel tk-devel bluez-libs-devel

# Install python 2.6 without overwriting python 2.4
# =================================================

VERSION=2.6.8
mkdir ~/src
chmod 777 ~/src
cd ~/src
wget http://www.python.org/ftp/python/$VERSION/Python-$VERSION.tgz
tar xvfz Python-2.6.8.tgz
cd Python-2.6.8
./configure --prefix=/opt/python2.6 --with-threads --enable-shared
make

# The altinstall ensures that python2.4 is left okay
# ==================================================

make altinstall
echo "/opt/python2.6/lib">/etc/ld.so.conf.d/opt-python2.6.conf
ldconfig

# create alias so that python 2.6 can be run with 'python2.6'
# ===========================================================

alias -p python2.6="/opt/python2.6/bin/python2.6"
ln -s /opt/python2.6/bin/python2.6 /usr/bin/python2.6

# Install uwsgi
# =========

version=uwsgi-1.2.3
cd /opt/
wget http://projects.unbit.it/downloads/$version.tar.gz
tar -zxvf $version.tar.gz
mv $version/ uwsgi/
cd uwsgi/

# build using python 2.6
# ======================

python2.6 setup.py build
python2.6 uwsgiconfig.py --build
useradd uwsgi

# create and own uwsgi log
# ========================
# Note this log will need emptying from time to time

echo " ">/var/log/uwsgi.log
chown uwsgi /var/log/uwsgi.log

# Install web2py
# ==========

cd /opt
mkdir web-apps
cd web-apps
wget http://www.web2py.com/examples/static/web2py_src.zip
unzip web2py_src.zip

# set the ownership for web2py application to uwsgi
# =================================================

cd web2py
chown -R uwsgi applications
chmod -R u+wx applications

# Now install nginx
# =================

cd /etc/yum.repos.d
echo "[nginx]">nginx.repo

echo "baseurl=http://nginx.org/packages/centos/5/"$basearch$"/">>nginx.repo
echo "gpgcheck=0">>nginx.repo
echo "enabled=1">>nginx.repo
yum install nginx

# We don't want the defaults, so remove them
# ==========================================

cd /etc/nginx/conf.d
mv default.conf default.conf.o
mv example_ssl.conf example_ssl.conf.o

# The following configuration files are also needed
# The options for uwsgi are in the following file. 
# It should be placed in /etc/uwsgi. Other options could be included.

echo """
[uwsgi]

uuid=uwsgi
pythonpath = /opt/web-apps/web2py
module = wsgihandler
socket=127.0.0.1:9001
harakiri 60
harakiri-verbose
enable-threads
daemonize = /var/log/uwsgi.log
""" > /etc/uwsgi/uwsgi_for_nginx.conf

# The next configuration file is for nginx, and goes in /etc/nginx/conf.d 
# It serves the static diretory of applications directly.
# I have not set up ssl because I access web2py admin by using ssh 
# tunneling and the web2py rocket server. 
# It should be straightforward to set up the ssl server however.

echo """
server {
  listen 80;
  server_name $hostname;
  location ~* /(\w+)/static/ {
    root /opt/web-apps/web2py/applications/;
  }
  location / {
    uwsgi_pass 127.0.0.1:9001;
    include uwsgi_params;
  }
}

#server {
#  listen 443;
#  server_name $hostname;
#  ssl on;
#  ssl_certificate /etc/nginx/ssl/web2py.crt;
#  ssl_certificate_key /etc/nginx/ssl/web2py.key;
#  location uwsgi_pass 127.0.0.1:9001;
#  include uwsgi_params;
#  uwsgi_param UWSGI_SCHEME $scheme;
#}
""" > /etc/nginx/conf.d/web2py.conf

# The final configuration file is only needed if you want to run 
# uwsgi as a service. It should be placed in /etc/init.d


echo  """

#!/bin/bash
# uwsgi - Use uwsgi to run python and wsgi web apps.
#
# chkconfig: - 85 15
# description: Use uwsgi to run python and wsgi web apps.
# processname: uwsgi
# author: Roman Vasilyev

# Source function library.
. /etc/rc.d/init.d/functions

###########################
PATH=/etc/uwsgi-python:/sbin:/bin:/usr/sbin:/usr/bin
PYTHONPATH=/home/www-data/web2py
MODULE=wsgihandler
prog=/etc/uwsgi-python/uwsgi
OWNER=uwsgi
# OWNER=nginx ¿?
NAME=uwsgi
DESC=uwsgi
DAEMON_OPTS="-s 127.0.0.1:9001 -M 4 -t 30 -A 4 -p 16 -b 32768 -d /var/log/$NAME.log --pidfile /var/run/$NAME.pid --uid $OWNER --ini-paste /etc/uwsgi-python/uwsgi_for_nginx.conf"
##############################

[ -f /etc/sysconfig/uwsgi ] && . /etc/sysconfig/uwsgi

lockfile=/var/lock/subsys/uwsgi

start () {
  echo -n "Starting $DESC: "
  daemon $prog $DAEMON_OPTS
  retval=$?
  echo
  [ $retval -eq 0 ] && touch $lockfile
  return $retval
}

stop () {
  echo -n "Stopping $DESC: "
  killproc $prog
  retval=$?
  echo
  [ $retval -eq 0 ] && rm -f $lockfile
  return $retval
}

reload () {
  echo "Reloading $NAME" 
  killproc $prog -HUP
  RETVAL=$?
  echo
}

force-reload () {
  echo "Reloading $NAME" 
  killproc $prog -TERM
  RETVAL=$?
  echo
}

restart () {
    stop
    start
}

rh_status () {
  status $prog
}

rh_status_q() {
  rh_status >/dev/null 2>&1
}

case "$1" in
  start)
    rh_status_q && exit 0
    $1
    ;;
  stop)
    rh_status_q || exit 0
    $1
    ;;
  restart|force-reload)
    $1
    ;;
  reload)
    rh_status_q || exit 7
    $1
    ;;
  status)
    rh_status
    ;;
  *)  
    echo "Usage: $0 {start|stop|restart|reload|force-reload|status}" >&2
    exit 2
    ;;
  esac
  exit 0

""" > /etc/init.d/uwsgi_nginx
