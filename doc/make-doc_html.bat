:: run from web2py root folder because of autodoc & web2py import behaviour!!!!
sphinx-build -b html -w doc\sphinx-build.log -Ea doc/source applications/examples/static/sphinx
::sphinx-build -b html -w sphinx-build.log -Ea source ../applications/examples/static/sphinx
