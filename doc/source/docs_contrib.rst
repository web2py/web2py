**********************************
Introduction for documenting
**********************************

.. rubric:: Some hints on writing documentation with Sphinx for web2py

Writing documentation
========================

official documentation
----------------------------------

* `Sphinx <http://sphinx.pocoo.org/contents.html>`_

Docstrings
------------------------
* official python standard
    * `Docstring Conventions <http://www.python.org/dev/peps/pep-0257>`_
    * `Documenting Python <http://docs.python.org/dev/documenting/index.html>`_
* numpy standard
    * `documentation standard <http://projects.scipy.org/scipy/numpy/wiki/CodingStyleGuidelines#docstring-standard>`_
    * `Example file <http://projects.scipy.org/numpy/browser/trunk/doc/example.py>`_
    * `Docstring Template <http://projects.scipy.org/numpy/browser/trunk/doc/EXAMPLE_DOCSTRING.txt>`_
       If you use `Eclipse / Pydev <http://pydev.sourceforge.net/>`_ you can define this piece as template.

Helpers
------------------------

Editors
________________________
* `Emacs: see docutils page <http://docutils.sourceforge.net/docs/user/emacs.html>`_
* `Gedit (Linux) <http://textmethod.com/wiki/ReStructuredTextToolsForGedit>`_
* `Ulipad (Win) <http://code.google.com/p/ulipad>`_

Others
________________________

* creating tables in ReST can be painful. Here is a module that can help::

    easy_install prettytable
    import prettytable as pt
    mytable =pt.PrettyTable(["id", "category", "recipie"])
    print mytable # copy & paste this into your ReST document!
    mytable_string = mytable.get_string() # or insert this string when
    generating automatic documents


Building documentation
========================
Follow these steps:

#. easy_install -U sphinx
#. built with custom make files for web2py => **Note: we could create a
   cross-platform python script for this!**

    #. unix-like: ``sh doc/make-doc_html.sh``
    #. windows: ``doc\make-doc_html.bat``

    Due to the special manner of the *web2py* import mechanism it requires that
    the doc is built from the *web2py* root directory.

#. the result will written to: ``web2py/applications/examples/static/sphinx``
   (the target directory will be automatically created)
#. inspect any error
    #. on the :term:`CLI`: see the errors and warnings floating on
       ``stderr``/``stdout``
    #. using the above mentioned make files a log file will be written to
       ``web2py/doc/sphinx-build.log``

Contributing
========================

.. warning:: Please ask on the
             `Mailinglist <http://groups.google.com/group/web2py>`_ before
             commiting or pushing to the repositories.

             So far, it has not been agreed on a proper setup to mutually
             edit the documentation and especially how to correct the
             docstrings without getting to many :term:`DVCS` conflicts.

#. branch the web2py Sphinx code::

    bzr branch lp:~web2py/web2py/web2py-sphinx
    cd web2py-sphinx

#. pull the latest code from web2py Sphinx branch::

    bzr pull

#. pull latest web2py development version::

    bzr pull http://bazaar.launchpad.net/~mdipierro/web2py/devel/

#. change and edit the documents or docstrings with your edior

#. push the changes to the web2py Sphinx branch::

    bzr push lp:~web2py/web2py/web2py-sphinx

   This requires that you are a member of the `web2py team at Launchpad <https://launchpad.net/~web2py>`_ and registered at Launchpad `with your SSA keys <https://help.launchpad.net/YourAccount/CreatingAnSSHKeyPair>`_. You can find more info on the `Launchpad help page <https://help.launchpad.net/Code/UploadingABranch>`_
