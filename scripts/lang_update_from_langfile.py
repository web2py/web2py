#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This script will update untranslated messages in target from source (target and source are both language files)
Usage:
    this can be used as first step when creating language file for new but very similar language
    or if you want update your app from welcome app of newer web2py version
    or in non-standard scenarios when you work on target and from any reason you have partial translation in source
"""

import sys
import os
sys.path.append(os.path.join(*__file__.split(os.sep)[:-2] or ['.']))

from gluon.languages import update_from_langfile
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Use to set untranslated messages in the translation file from another one.')
    parser.add_argument(
        '-t', '--target',
        required=True,
        dest="target",
        help="Specify language file (rw) where untranslated messages will be updated if possible"
    )
    parser.add_argument(
        '-s', '--source',
        required=True,
        dest="source",
        help="Specify language file (ro) where seek for translations"
    )
    parser.add_argument(
        '-f', '--force-update',
        dest="force_update",
        action="store_true",
        default=False,
        help="without it: add new + translate untranslated, if used: in addition update items if translation differs"
    )
    args = parser.parse_args()

    update_from_langfile(args.target, args.source, force_update=args.force_update)

    print '%s was updated.' % args.target
