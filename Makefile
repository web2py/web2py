clean:
	rm -f httpserver.log 
	rm -f parameters*.py 
	rm -f -r applications/*/compiled     	
	find ./ -name '*~' -exec rm -f {} \; 
	find ./ -name '*.orig' -exec rm -f {} \; 
	find ./ -name '*.rej' -exec rm -f {} \; 
	find ./ -name '#*' -exec rm -f {} \;
	find ./ -name 'Thumbs.db' -exec rm -f {} \; 
	find ./gluon/ -name '.*' -exec rm -f {} \;
	find ./gluon/ -name '*class' -exec rm -f {} \; 
	find ./applications/admin/ -name '.*' -exec rm -f {} \; 
	find ./applications/examples/ -name '.*' -exec rm -f {} \; 
	find ./applications/welcome/ -name '.*' -exec rm -f {} \; 
	find ./ -name '*.pyc' -exec rm -f {} \;
all:
	echo "The Makefile is used to build the distribution."
	echo "In order to run web2py you do not need to make anything."
	echo "just run web2py.py"
epydoc:
	### build epydoc
	rm -f -r applications/examples/static/epydoc/ 
	epydoc --config epydoc.conf
	cp applications/examples/static/title.png applications/examples/static/epydoc
tests:
	cd gluon/tests; ./test.sh 1>tests.log 2>&1 
update:
	wget -O gluon/contrib/feedparser.py http://feedparser.googlecode.com/svn/trunk/feedparser/feedparser.py
	wget -O gluon/contrib/simplejsonrpc.py http://rad2py.googlecode.com/hg/ide2py/simplejsonrpc.py
src:
	echo 'Version 1.99.7 ('`date +%Y-%m-%d\ %H:%M:%S`') stable' > VERSION
	### rm -f all junk files
	make clean
	### clean up baisc apps
	rm -f routes.py 
	rm -f applications/*/sessions/*       
	rm -f applications/*/errors/* | echo 'too many files'
	rm -f applications/*/cache/*                  
	rm -f applications/admin/databases/*                 
	rm -f applications/welcome/databases/*               
	rm -f applications/examples/databases/*             
	rm -f applications/admin/uploads/*                 
	rm -f applications/welcome/uploads/*               
	rm -f applications/examples/uploads/*             
	### make admin layout and appadmin the default
	cp applications/admin/views/appadmin.html applications/welcome/views
	cp applications/admin/views/appadmin.html applications/examples/views
	cp applications/admin/controllers/appadmin.py applications/welcome/controllers
	cp applications/admin/controllers/appadmin.py applications/examples/controllers	
	### build web2py_src.zip
	echo '' > NEWINSTALL
	mv web2py_src.zip web2py_src_old.zip | echo 'no old'
	cd ..; zip -r web2py/web2py_src.zip web2py/gluon/*.py web2py/gluon/contrib/* web2py/splashlogo.gif web2py/*.py web2py/README  web2py/LICENSE web2py/CHANGELOG web2py/NEWINSTALL web2py/VERSION web2py/Makefile web2py/epydoc.css web2py/epydoc.conf web2py/app.example.yaml web2py/logging.example.conf web2py_exe.conf web2py/queue.example.yaml MANIFEST.in w2p_apps w2p_clone w2p_run startweb2py web2py/scripts/*.sh web2py/scripts/*.py web2py/applications/admin web2py/applications/examples/ web2py/applications/welcome web2py/applications/__init__.py web2py/site-packages/__init__.py web2py/gluon/tests/*.sh web2py/gluon/tests/*.py

mdp:
	make epydoc
	make src
	make app
	make win
app:
	echo 'did you uncomment import_all in gluon/main.py?'
	python2.5 -c 'import compileall; compileall.compile_dir("gluon/")'
	#python web2py.py -S welcome -R __exit__.py
	find gluon -path '*.pyc' -exec cp {} ../web2py_osx/site-packages/{} \;
	cd ../web2py_osx/site-packages/; zip -r ../site-packages.zip *
	mv ../web2py_osx/site-packages.zip ../web2py_osx/web2py/web2py.app/Contents/Resources/lib/python2.5
	cp README ../web2py_osx/web2py/web2py.app/Contents/Resources
	cp NEWINSTALL ../web2py_osx/web2py/web2py.app/Contents/Resources
	cp LICENSE ../web2py_osx/web2py/web2py.app/Contents/Resources
	cp VERSION ../web2py_osx/web2py/web2py.app/Contents/Resources
	cp CHANGELOG ../web2py_osx/web2py/web2py.app/Contents/Resources
	cp splashlogo.gif ../web2py_osx/web2py/web2py.app/Contents/Resources
	cp options_std.py ../web2py_osx/web2py/web2py.app/Contents/Resources
	cp routes.example.py ../web2py_osx/web2py/web2py.app/Contents/Resources
	cp router.example.py ../web2py_osx/web2py/web2py.app/Contents/Resources
	cp app.example.yaml ../web2py_osx/web2py/web2py.app/Contents/Resources
	cp queue.example.yaml ../web2py_osx/web2py/web2py.app/Contents/Resources
	cp -r applications/admin ../web2py_osx/web2py/web2py.app/Contents/Resources/applications
	cp -r applications/welcome ../web2py_osx/web2py/web2py.app/Contents/Resources/applications
	cp -r applications/examples ../web2py_osx/web2py/web2py.app/Contents/Resources/applications
	cp applications/__init__.py ../web2py_osx/web2py/web2py.app/Contents/Resources/applications
	cd ../web2py_osx; zip -r web2py_osx.zip web2py
	mv ../web2py_osx/web2py_osx.zip .
win:
	echo 'did you uncomment import_all in gluon/main.py?'
	python2.5 -c 'import compileall; compileall.compile_dir("gluon/")'
	find gluon -path '*.pyc' -exec cp {} ../web2py_win/library/{} \;
	cd ../web2py_win/library/; zip -r ../library.zip *
	mv ../web2py_win/library.zip ../web2py_win/web2py
	cp README ../web2py_win/web2py/
	cp NEWINSTALL ../web2py_win/web2py/
	cp LICENSE ../web2py_win/web2py/
	cp VERSION ../web2py_win/web2py/
	cp CHANGELOG ../web2py_win/web2py/
	cp splashlogo.gif ../web2py_win/web2py/
	cp options_std.py ../web2py_win/web2py/
	cp routes.example.py ../web2py_win/web2py/
	cp router.example.py ../web2py_win/web2py/
	cp app.example.yaml ../web2py_win/web2py/
	cp queue.example.yaml ../web2py_win/web2py/
	cp -r applications/admin ../web2py_win/web2py/applications
	cp -r applications/welcome ../web2py_win/web2py/applications
	cp -r applications/examples ../web2py_win/web2py/applications
	cp applications/__init__.py ../web2py_win/web2py/applications
	cd ../web2py_win; zip -r web2py_win.zip web2py
	mv ../web2py_win/web2py_win.zip .
pip:
	# create Web2py distribution for upload to Pypi
	# after upload clean Web2py sources with rm -R ./dist
	python setup.py sdist
run:
	python2.5 web2py.py -a hello
commit:
	make src
	echo '' > NEWINSTALL
	hg commit -m "$(S)"
	#bzr commit -m "$(S)"
	git commit -a -m "$(S)"
push:
	hg push
	git push
	#bzr push bzr+ssh://mdipierro@bazaar.launchpad.net/~mdipierro/web2py/devel --use-existing-dir
