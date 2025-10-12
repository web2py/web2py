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
	find . -name '*.pyc' -exec rm -f {} \;
	find . -name 'Thumbs.db' -exec rm -f {} \;
	find . -name '__pycache__' -type d -exec rm -rf {} \; || true
	find applications/admin/ -name '.*' -exec rm -f {} \;
	find applications/examples/ -name '.*' -exec rm -f {} \;
	find applications/welcome/ -name '.*' -exec rm -f {} \;
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
tests:
	python web2py.py --verbose --run_system_tests
build:
	pip install --upgrade build
	pip install --upgrade twine
	python -m build
deploy: build
	python -m twine upload dist/*
install:
	python -m pip install .
coverage:
	coverage erase --rcfile=gluon/tests/coverage.ini
	export COVERAGE_PROCESS_START=gluon/tests/coverage.ini
	python web2py.py --verbose --run_system_tests --with_coverage
	coverage combine --rcfile=gluon/tests/coverage.ini
	sleep 1
	coverage html --rcfile=gluon/tests/coverage.ini
src:
	### Use semantic versioning
	echo 'VERSION = "3.0.14-stable+timestamp.'`date +%Y.%m.%d.%H.%M.%S`'"' > gluon/version.py
	### rm -f all junk files
	make clean
	### make welcome layout and appadmin the default
	cp applications/welcome/views/appadmin.html applications/admin/views
	cp applications/welcome/views/appadmin.html applications/examples/views
	cp applications/welcome/controllers/appadmin.py applications/admin/controllers
	cp applications/welcome/controllers/appadmin.py applications/examples/controllers	
	### build web2py_src.zip
	echo '' > NEWINSTALL
	mv binaries/web2py_src.zip binaries/web2py_src_old.zip | true
	cd ..; zip -r --exclude=**.git** --exclude=**.tox** --exclude=**_pycache__** web2py/binaries/web2py_src.zip web2py/web2py.py web2py/anyserver.py web2py/fabfile.py web2py/gluon/* web2py/extras/* web2py/handlers/* web2py/examples/* web2py/README.markdown  web2py/LICENSE web2py/CHANGELOG web2py/NEWINSTALL web2py/VERSION web2py/MANIFEST.in web2py/scripts/*.sh web2py/scripts/*.py web2py/applications/admin web2py/applications/examples/ web2py/applications/welcome web2py/applications/__init__.py web2py/site-packages/__init__.py web2py/gluon/tests/*.sh web2py/gluon/tests/*.py
win:
	make clean
	$(eval TMPDIR := $(shell mktemp -d))
	mkdir -p $(TMPDIR)
	mkdir -p $(TMPDIR)/web2py_win
	cp binaries/web2py_win32_py312.zip $(TMPDIR)/web2py_win
	cd $(TMPDIR)/web2py_win; unzip web2py_win32_py312.zip; rm web2py_win32_py312.zip	
	find gluon -path '*.py' -exec cp -r --parents {} $(TMPDIR)/web2py_win/web2py/ \;
	cp README.md $(TMPDIR)/web2py_win/web2py/
	cp NEWINSTALL $(TMPDIR)/web2py_win/web2py/
	cp ABOUT.web2py.txt $(TMPDIR)/web2py_win/web2py/
	cp LICENSE.web2py.txt $(TMPDIR)/web2py_win/web2py/
	cp CHANGELOG.md $(TMPDIR)/web2py_win/web2py/
	cp -r applications/admin $(TMPDIR)/web2py_win/web2py/applications
	cp -r applications/welcome $(TMPDIR)/web2py_win/web2py/applications
	cp -r applications/examples $(TMPDIR)/web2py_win/web2py/applications
	cp applications/__init__.py $(TMPDIR)/web2py_win/web2py/applications
	cd $(TMPDIR)/web2py_win/ && rm -f web2py_win32_py312.zip && zip -r web2py_win32_py312.zip web2py
	ls -l $(TMPDIR)/web2py_win/web2py_win32_py312.zip
	mv $(TMPDIR)/web2py_win/web2py_win32_py312.zip binaries/
	rm -rf $(TMPDIR)
run:
	python web2py.py -a hello
