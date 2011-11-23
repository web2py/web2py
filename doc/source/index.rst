.. Web2Py documentation master file, created by
   sphinx-quickstart on Thu Apr 30 17:10:06 2009.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Web2Py's documentation!
==================================

.. warning:: This is a BETA version of the Sphinx based documentation for
             *web2py*. **It is subject to change!**

.. note::    The documentation at the current stage is intended for develpers
             and contributors. They shall have the possibility to test their
             docstrings and markup.

.. note:: Please read :doc:`docs_contrib` for instructions to Sphinx
          documentation writing for *web2py*!

Contents
===================

General Documents
-------------------
.. toctree::
   :maxdepth: 2

   docs_contrib
   docs_overview
   web2py_todo
   glossary

Contributed Documents
------------------------
.. toctree::
   :maxdepth: 1

   user_wiki
   faq



..        User Wiki
        -------------------

        .. rubric:: The pages from the `User Wiki <https://mdp.cti.depaul.edu/wiki>`_

        .. note:: According to an `ongoing discussion <http://thread.gmane.org/gmane.comp.python.web2py/8304/focus=8512>`_,
                  the page order and structure may be
                  changed in the future.

        .. on error do::

            rename 's/\.txt/\.rst/' *.txt

        .. toctree::
           :maxdepth: 2
           :glob:

           user_wiki/*


..    Frequently Asked Questions (FAQ)
    ----------------------------------

    .. rubric:: The pages from the `AlterEgo <http://www.web2py.com/AlterEgo>`_

    .. note:: These pages are extracted as plain and not yet converted into
              :term:`ReSt` formated documents.

    .. toctree::
       :maxdepth: 2
       :glob:

       faq/*

Modules
-------------------

.. toctree::
   :maxdepth: 2


   modules


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
