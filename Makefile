all:
	@echo "The Makefile is used to build the distribution."
	@echo "In order to run web2py you do not need to make anything."
	@echo "just run web2py.py"
clean:
	rm -f httpserver.log 
	rm -f parameters*.py 
	rm -f -r applications/*/compiled
	find . -name '*~' -exec rm -f {} \; 
	find . -name '*.orig' -exec rm -f {} \; 
	find . -name '*.rej' -exec rm -f {} \; 
	find . -name '#*' -exec rm -f {} \;
	find . -name 'Thumbs.db' -exec rm -f {} \; 
	# find . -name '.tox' -exec rm -rf {} \; 
	# find . -name '__pycache__' -exec rm -rf {} \; 
	find gluon/ -name '*class' -exec rm -f {} \; 
	find applications/admin/ -name '.*' -exec rm -f {} \; 
	find applications/examples/ -name '.*' -exec rm -f {} \; 
	find applications/welcome/ -name '.*' -exec rm -f {} \; 
	find . -name '*.pyc' -exec rm -f {} \;
tests:
	python web2py.py --verbose --run_system_tests
coverage:
	coverage erase --rcfile=gluon/tests/coverage.ini
	export COVERAGE_PROCESS_START=gluon/tests/coverage.ini
	python web2py.py --verbose --run_system_tests --with_coverage
	coverage combine --rcfile=gluon/tests/coverage.ini
	sleep 1
	coverage html --rcfile=gluon/tests/coverage.ini
update:
	wget -O gluon/contrib/feedparser.py http://feedparser.googlecode.com/svn/trunk/feedparser/feedparser.py
	wget -O gluon/contrib/simplejsonrpc.py http://rad2py.googlecode.com/hg/ide2py/simplejsonrpc.py
	echo "remember that pymysql was tweaked"
rmfiles:
	### clean up baisc apps
	rm -f routes.py 
	rm -rf applications/*/sessions/*
	rm -rf applications/*/errors/* | echo 'too many files'
	rm -rf applications/*/cache/*
	rm -rf applications/admin/databases/*                 
	rm -rf applications/welcome/databases/*               
	rm -rf applications/examples/databases/*             
	rm -rf applications/admin/uploads/*                 
	rm -rf applications/welcome/uploads/*               
	rm -rf applications/examples/uploads/* 
src:
	### Use semantic versioning
	echo 'Version 2.21.1-stable+timestamp.'`date +%Y.%m.%d.%H.%M.%S` > VERSION
	### rm -f all junk files
	make clean
	# make rmfiles
	### make welcome layout and appadmin the default
	cp applications/welcome/views/appadmin.html applications/admin/views
	cp applications/welcome/views/appadmin.html applications/examples/views
	cp applications/welcome/controllers/appadmin.py applications/admin/controllers
	cp applications/welcome/controllers/appadmin.py applications/examples/controllers	
	### build web2py_src.zip
	echo '' > NEWINSTALL
	mv web2py_src.zip web2py_src_old.zip | echo 'no old'
	cd ..; zip -r --exclude=**.git** --exclude=**.tox** --exclude=**_pycache__** web2py/web2py_src.zip web2py/web2py.py web2py/anyserver.py web2py/fabfile.py web2py/gluon/* web2py/extras/* web2py/handlers/* web2py/examples/* web2py/README.markdown  web2py/LICENSE web2py/CHANGELOG web2py/NEWINSTALL web2py/VERSION web2py/MANIFEST.in web2py/scripts/*.sh web2py/scripts/*.py web2py/applications/admin web2py/applications/examples/ web2py/applications/welcome web2py/applications/__init__.py web2py/site-packages/__init__.py web2py/gluon/tests/*.sh web2py/gluon/tests/*.py

mdp:
	make src
	make app
	make win
app:
	python2.7 -c 'import compileall; compileall.compile_dir("gluon/")'
	#python web2py.py -S welcome -R __exit__.py
	#cd ../web2py_osx/site-packages/; unzip ../site-packages.zip
	#find gluon -path '*.pyc' -exec cp {} ../web2py_osx/site-packages/{} \;
	#cd ../web2py_osx/site-packages/; zip -r ../site-packages.zip *
	cp ../web2py_osx/site-packages.zip ../web2py_osx/web2py/web2py.app/Contents/Resources/lib/python2.7
	find gluon -path '*.py' -exec cp -r --parents {} ../web2py_osx/web2py/web2py.app/Contents/Resources/ \;
	cp README.markdown ../web2py_osx/web2py/web2py.app/Contents/Resources
	cp NEWINSTALL ../web2py_osx/web2py/web2py.app/Contents/Resources
	cp LICENSE ../web2py_osx/web2py/web2py.app/Contents/Resources
	cp VERSION ../web2py_osx/web2py/web2py.app/Contents/Resources
	cp CHANGELOG ../web2py_osx/web2py/web2py.app/Contents/Resources
	cp -r extras ../web2py_osx/web2py/web2py.app/Contents/Resources
	cp -r examples ../web2py_osx/web2py/web2py.app/Contents/Resources
	cp -r applications/admin ../web2py_osx/web2py/web2py.app/Contents/Resources/applications
	cp -r applications/welcome ../web2py_osx/web2py/web2py.app/Contents/Resources/applications
	cp -r applications/examples ../web2py_osx/web2py/web2py.app/Contents/Resources/applications
	cp applications/__init__.py ../web2py_osx/web2py/web2py.app/Contents/Resources/applications
	cd ../web2py_osx; zip -r web2py_osx.zip web2py
		
	mv ../web2py_osx/web2py_osx.zip .
win:
	#cd ../web2py_win/library/; zip -r ../library.zip *
	cp ../web2py_win/library.zip ../web2py_win/web2py
	find gluon -path '*.py' -exec cp -r --parents {} ../web2py_win/web2py/ \;
	cp README.markdown ../web2py_win/web2py/
	cp NEWINSTALL ../web2py_win/web2py/
	cp LICENSE ../web2py_win/web2py/
	cp VERSION ../web2py_win/web2py/
	cp CHANGELOG ../web2py_win/web2py/
	cp -r extras ../web2py_win/web2py/
	cp -r examples ../web2py_win/web2py/
	cp -r applications/admin ../web2py_win/web2py/applications
	cp -r applications/welcome ../web2py_win/web2py/applications
	cp -r applications/examples ../web2py_win/web2py/applications
	cp applications/__init__.py ../web2py_win/web2py/applications
	# per https://github.com/web2py/web2py/issues/1716
	mv ../web2py_win/web2py/_ssl.pyd ../web2py_win/web2py/_ssl.pyd.legacy | echo 'done'
	cd ../web2py_win; zip -r web2py_win.zip web2py
	mv ../web2py_win/web2py_win.zip .
binaries:
	echo '' > NEWINSTALL
	cp VERSION ../web2py_win_py27/web2py/
	cp README.markdown ../web2py_win_py27/web2py/
	cp NEWINSTALL ../web2py_win_py27/web2py/
	cp LICENSE ../web2py_win_py27/web2py/
	cp CHANGELOG ../web2py_win_py27/web2py/
	rm -rf ../web2py_win_py27/web2py/gluon
	cp -r gluon ../web2py_win_py27/web2py/gluon
	rm -rf ../web2py_win_py27/web2py/applications/*
	cp -r applications/__init__.py ../web2py_win_py27/web2py/applications/
	cp -r applications/admin ../web2py_win_py27/web2py/applications/
	cp -r applications/welcome ../web2py_win_py27/web2py/applications/
	cp -r applications/examples ../web2py_win_py27/web2py/applications/
	cd ../web2py_win_py27; zip -r ../web2py/web2py_win_py27.zip web2py

	cp VERSION ../web2py_win_py37/web2py/
	cp README.markdown ../web2py_win_py37/web2py/
	cp NEWINSTALL ../web2py_win_py37/web2py/
	cp LICENSE ../web2py_win_py37/web2py/
	cp CHANGELOG ../web2py_win_py37/web2py/
	rm -rf ../web2py_win_py37/web2py/gluon
	cp -r gluon ../web2py_win_py37/web2py/gluon
	rm -rf ../web2py_win_py37/web2py/applications/*
	cp -r applications/__init__.py ../web2py_win_py37/web2py/applications/
	cp -r applications/admin ../web2py_win_py37/web2py/applications/
	cp -r applications/welcome ../web2py_win_py37/web2py/applications/
	cp -r applications/examples ../web2py_win_py37/web2py/applications/
	cd ../web2py_win_py37; zip -r ../web2py/web2py_win_py37.zip web2py

	cp VERSION ../web2py_osx_py27/web2py.app/Contents/MacOS/
	cp README.markdown ../web2py_osx_py27/web2py.app/Contents/MacOS/
	cp NEWINSTALL ../web2py_osx_py27/web2py.app/Contents/MacOS/
	cp LICENSE ../web2py_osx_py27/web2py.app/Contents/MacOS/
	cp CHANGELOG ../web2py_osx_py27/web2py.app/Contents/MacOS/	
	rm -rf ../web2py_osx_py27/web2py.app/Contents/MacOS/gluon
	cp -r gluon ../web2py_osx_py27/web2py.app/Contents/MacOS/gluon
	rm -rf ../web2py_osx_py27/web2py.app/Contents/MacOS/applications/*
	cp -r applications/__init__.py ../web2py_osx_py27/web2py.app/Contents/MacOS/applications/
	cp -r applications/admin ../web2py_osx_py27/web2py.app/Contents/MacOS/applications/
	cp -r applications/welcome ../web2py_osx_py27/web2py.app/Contents/MacOS/applications/
	cp -r applications/examples ../web2py_osx_py27/web2py.app/Contents/MacOS/applications/
	cd ../web2py_osx_py27; zip -r ../web2py/web2py_osx_py27.zip web2py.app

	cp VERSION ../web2py_osx_py37/web2py.app/Contents/MacOS/
	cp README.markdown ../web2py_osx_py37/web2py.app/Contents/MacOS/
	cp NEWINSTALL ../web2py_osx_py37/web2py.app/Contents/MacOS/
	cp LICENSE ../web2py_osx_py37/web2py.app/Contents/MacOS/
	cp CHANGELOG ../web2py_osx_py37/web2py.app/Contents/MacOS/	
	rm -rf ../web2py_osx_py37/web2py.app/Contents/MacOS/gluon
	cp -r gluon ../web2py_osx_py37/web2py.app/Contents/MacOS/gluon
	rm -rf ../web2py_osx_py37/web2py.app/Contents/MacOS/applications/*
	cp -r applications/__init__.py ../web2py_osx_py37/web2py.app/Contents/MacOS/applications/
	cp -r applications/admin ../web2py_osx_py37/web2py.app/Contents/MacOS/applications/
	cp -r applications/welcome ../web2py_osx_py37/web2py.app/Contents/MacOS/applications/
	cp -r applications/examples ../web2py_osx_py37/web2py.app/Contents/MacOS/applications/
	cd ../web2py_osx_py37; zip -r ../web2py/web2py_osx_py37.zip web2py.app
run:
	python2.7 web2py.py -a hello
commit:
	python web2py.py --run_system_tests
	make src
	echo '' > NEWINSTALL
	hg commit -m "$(S)"
	git commit -a -m "$(S)"
push:
	hg push
	git push
	git push --tags
tag:
	git tag -l '$(S)'
	hg tag -l '$(S)'
	make commit S='$(S)'
	make push
pip:
	# create Web2py distribution for upload to Pypi
	# after upload clean Web2py sources with rm -R ./dist
	# http://guide.python-distribute.org/creation.html
	python setup.py sdist
	sudo python setup.py register
	sudo python setup.py sdist upload
