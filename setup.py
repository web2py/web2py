#!/usr/bin/env python3

import logging
import setuptools
from setuptools import setup

import tarfile
import os, sys

from setupbase import (
    UpdateSubmodules,
    check_submodule_status,
    update_submodules,
    require_clean_submodules
)

#-------------------------------------------------------------------------------
# Make sure we aren't trying to run without submodules
#-------------------------------------------------------------------------------
here = os.path.abspath(os.path.dirname(__file__))
require_clean_submodules(here, sys.argv)


from gluon.fileutils import tar, untar, read_file, write_file


def tar(file, filelist, expression='^.+$'):
    """
    tars dir/files into file, only tars file that match expression
    """

    tar = tarfile.TarFile(file, 'w')
    try:
        for element in filelist:
            try:
                for file in os.listdir(element, expression, add_dirs=True):
                    tar.add(os.path.join(element, file), file, False)
            except:
                tar.add(element)
    finally:
        tar.close()


def start():
    logging.basicConfig(level=logging.DEBUG)  # Configure logging level (optional)

    if 'sdist' in sys.argv:
        tar('gluon/env.tar', ['applications', 'VERSION',
                              'extras/icons/splashlogo.gif'])

    setup(name='web2py',
          version=read_file("VERSION").split()[1],
          description="""full-stack framework for rapid development and prototyping
          of secure database-driven web-based applications, written and
          programmable in Python.""",
          long_description="""
          Everything in one package with no dependencies. Development, deployment,
          debugging, testing, database administration and maintenance of applications can
          be done via the provided web interface. web2py has no configuration files,
          requires no installation, can run off a USB drive. web2py uses Python for the
          Model, the Views and the Controllers, has a built-in ticketing system to manage
          errors, an internationalization engine, works with SQLite, PostgreSQL, MySQL,
          MSSQL, FireBird, Oracle, IBM DB2, Informix, Ingres,
