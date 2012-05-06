## Readme

web2py is a free open source full-stack framework for rapid development of fast, scalable, secure and portable database-driven web-based applications. 

It is written and programmable in Python. LGPLv3 License

Learn more at http://web2py.com

## Installation Instructions

To start web2py there is NO NEED to install it. Just unzip and do:

    python web2py.py

That's it!!!

## web2py directory structure

    project/
        README
        LICENSE
        VERSION                    > this web2py version
        web2py.py                  > the startup script
        anyserver.py               > to run with third party servers
        wsgihandler.py             > handler to connect to WSGI
        ...                        > other handlers and example files
        gluon/                     > the core libraries
            contrib/               > third party libraries
            tests/                 > unittests
        applications/              > are the apps
	    admin/                 > web based IDE
                ...
            examples/              > examples, docs, links
                ...
            welcome/               > the scaffolding app (they all copy it)
                ABOUT
                LICENSE
                models/
                views/
                controllers/
                sessions/
                errors/
                cache/
                static/
                uploads/
                modules/
                cron/
                tests/
            ...                    > your own apps
        scripts/                   > utility and installation scripts
        site-packages/             > additional optional modules


## Issues?

Report issues at http://code.google.com/p/web2py/issues/
