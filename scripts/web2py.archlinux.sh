#!/bin/bash
# the script should be run
# from WEB2PY root directory

prog=`basename $0`

cd `pwd`
chmod +x $prog

function web2py_start {
  nohup ./$prog -a "<recycle>" 2>/dev/null &
  pid=`pgrep $prog | tail -1`
  if [ $pid -ne $$ ]
  then
    echo "WEB2PY has been started."
  fi
}
function web2py_stop {
  kill -15 `pgrep $prog | grep -v $$` 2>/dev/null
  pid=`pgrep $prog | head -1`
  if [ $pid -ne $$ ]
  then
    echo "WEB2PY has been stopped."
  fi
}

case "$1" in
  start)
    web2py_start
  ;;
  stop)
    web2py_stop
  ;;
  restart)
    web2py_stop
    web2py_start
  ;;
  *)
    echo "Usage: $prog [start|stop|restart]"
  ;;
esac

exit 0

