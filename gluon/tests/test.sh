#!/bin/sh
#
#  run unit tests under nose if available,
#  optionally with coverage
#
#  test.sh [cover [gluon.rewrite]]
#
#  easy_install nose
#  easy_install coverage
#
NOSETESTS=nosetests
COVER=gluon		# change to (eg) gluon.rewrite to collect coverage stats on a single module
PROCESSES=4

WHICH=`which $NOSETESTS`
if [ "$WHICH" == "" ]; then
	# if nose isn't available, run the tests directly
	for testmod in test_*.py; do
		python $testmod
	done
else
	if [ "$1" = "cover" ]; then
		# note: coverage doesn't handle multiple processes
		if [ "$2" != "" ]; then
			COVER=$2
		fi
		$NOSETESTS --with-coverage --cover-package=$COVER --cover-erase
	elif [ "$1" = "doctest" ]; then
		# this has to run in gluon's parent; needs work
		#
		# the problem is that doctests run this way have a very different environment,
		# apparently due to imports that don't happen in the normal course of running
		# doctest via __main__.
		#
		echo doctest not supported >&2
		exit 1
		if [ ! -d gluon ]; then
			cd ../..
		fi
		$NOSETESTS --with-doctest
	else
		$NOSETESTS --processes=$PROCESSES
	fi
fi

