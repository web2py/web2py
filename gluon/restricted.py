#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
| This file is part of the web2py Web Framework
| Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
| License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)

Restricted environment to execute application's code
-----------------------------------------------------
"""

import builtins
import importlib
import io
import logging
import os
import pickle
import sys
import traceback
import types

from gluon.html import BEAUTIFY, XML
from gluon.http import HTTP
from gluon.settings import global_settings
from gluon.storage import Storage

logger = logging.getLogger("web2py")

__all__ = [
    "RestrictedError",
    "restricted",
    "TicketStorage",
    "compile2",
    "SafeUnpickler",
    "safe_load",
    "safe_loads",
]

DEFAULT_SAFE_GLOBALS = {
    "decimal": {"Decimal"},
    "datetime": {"date", "datetime", "time", "timedelta"},
    "uuid": {"UUID"},
    "pydal.objects": {"Row", "Rows"},
}


class SafeUnpickler(pickle.Unpickler):
    """
    Restricted unpickler that only allows a small set of safe builtins
    and a small set of safe globals.
    """

    safe_builtins = {
        "dict",
        "list",
        "tuple",
        "set",
        "frozenset",
        "str",
        "bytes",
        "bytearray",
        "int",
        "float",
        "complex",
        "bool",
        "NoneType",
    }

    def __init__(self, file_obj, allowed_classes=None):
        super(SafeUnpickler, self).__init__(file_obj)
        self.allowed_classes = self._normalize_allowed_classes(allowed_classes)

    @staticmethod
    def _normalize_allowed_classes(allowed_classes):
        if not allowed_classes:
            return {}
        normalized = {}
        for module, names in allowed_classes.items():
            if isinstance(names, str):
                normalized[module] = {names}
            else:
                normalized[module] = set(names)
        return normalized

    def find_class(self, module, name):
        if module == "builtins" and name in self.safe_builtins:
            return getattr(builtins, name)
        if module in DEFAULT_SAFE_GLOBALS and name in DEFAULT_SAFE_GLOBALS[module]:
            try:
                mod = importlib.import_module(module)
            except ImportError:
                raise pickle.UnpicklingError(
                    "global '%s.%s' is forbidden" % (module, name)
                )
            return getattr(mod, name)
        if module in self.allowed_classes and name in self.allowed_classes[module]:
            try:
                mod = importlib.import_module(module)
            except ImportError:
                raise pickle.UnpicklingError(
                    "global '%s.%s' is forbidden" % (module, name)
                )
            return getattr(mod, name)
        logger.warning("SafeUnpickler blocked: '%s.%s'", module, name)
        raise pickle.UnpicklingError("global '%s.%s' is forbidden" % (module, name))


def safe_load(file_obj, allowed_classes=None):
    return SafeUnpickler(file_obj, allowed_classes=allowed_classes).load()


def safe_loads(data, allowed_classes=None):
    if isinstance(data, str):
        data = data.encode("latin-1")
    return SafeUnpickler(io.BytesIO(data), allowed_classes=allowed_classes).load()


class TicketStorage(Storage):
    """
    Defines the ticket object and the default values of its members (None)
    """

    def __init__(self, db=None, tablename="web2py_ticket"):
        Storage.__init__(self)
        self.db = db
        self.tablename = tablename

    def store(self, request, ticket_id, ticket_data):
        """
        Stores the ticket. It will figure out if this must be on disk or in db
        """
        if self.db:
            self._store_in_db(request, ticket_id, ticket_data)
        else:
            self._store_on_disk(request, ticket_id, ticket_data)

    def _store_in_db(self, request, ticket_id, ticket_data):
        self.db._adapter.reconnect()
        try:
            table = self._get_table(self.db, self.tablename, request.application)
            table.insert(
                ticket_id=ticket_id,
                ticket_data=pickle.dumps(ticket_data, pickle.HIGHEST_PROTOCOL),
                created_datetime=request.now,
            )
            self.db.commit()
            message = "In FILE: %(layer)s\n\n%(traceback)s\n"
        except Exception:
            self.db.rollback()
            message = " Unable to store in FILE: %(layer)s\n\n%(traceback)s\n"
        self.db.close()
        logger.error(message % ticket_data)

    def _store_on_disk(self, request, ticket_id, ticket_data):
        ef = self._error_file(request, ticket_id, "wb")
        try:
            pickle.dump(ticket_data, ef)
        finally:
            ef.close()

    def _error_file(self, request, ticket_id, mode, app=None):
        root = request.folder
        if app:
            root = os.path.join(os.path.join(root, ".."), app)
        errors_folder = os.path.abspath(
            os.path.join(root, "errors")
        )  # .replace('\\', '/')
        return open(os.path.join(errors_folder, ticket_id), mode)

    def _get_table(self, db, tablename, app):
        tablename = tablename + "_" + app
        table = db.get(tablename)
        if not table:
            table = db.define_table(
                tablename,
                db.Field("ticket_id", length=100),
                db.Field("ticket_data", "text"),
                db.Field("created_datetime", "datetime"),
            )
        return table

    # gluon.html.XML objects are stored in ticket snapshots for request/response/session.
    # XML uses XML_unpickle as its __reduce__ helper, so both must be allowed.
    TICKET_ALLOWED_CLASSES = {"gluon.html": {"XML", "XML_unpickle"}}

    def load(
        self,
        request,
        app,
        ticket_id,
    ):
        if not self.db:
            try:
                ef = self._error_file(request, ticket_id, "rb", app)
            except IOError:
                return {}
            try:
                return safe_load(ef, allowed_classes=self.TICKET_ALLOWED_CLASSES)
            except (pickle.UnpicklingError, EOFError):
                return {}
            finally:
                ef.close()
        else:
            table = self._get_table(self.db, self.tablename, app)
            rows = self.db(table.ticket_id == ticket_id).select()
            if not rows:
                return {}
            try:
                return safe_loads(rows[0].ticket_data, allowed_classes=self.TICKET_ALLOWED_CLASSES)
            except (pickle.UnpicklingError, EOFError):
                return {}


class RestrictedError(Exception):
    """
    Class used to wrap an exception that occurs in the restricted environment
    below. The traceback is used to log the exception and generate a ticket.
    """

    def __init__(
        self,
        layer="",
        code="",
        output="",
        environment=None,
    ):
        """
        Layer here is some description of where in the system the exception
        occurred.
        """
        if environment is None:
            environment = {}
        self.layer = layer
        self.code = code
        self.output = output
        self.environment = environment
        if layer:
            try:
                try:
                    self.traceback = traceback.format_exc()
                except:
                    self.traceback = traceback.format_exc(limit=1)
            except:
                self.traceback = "no traceback because template parsing error"
            try:
                self.snapshot = snapshot(
                    context=10, code=code, environment=self.environment
                )
            except Exception as e:
                self.snapshot = {}
                logger.warning("snapshot() failed: %s", e)
        else:
            self.traceback = "(no error)"
            self.snapshot = {}

    def log(self, request):
        """
        Logs the exception.
        """
        try:
            d = {
                "layer": str(self.layer),
                "code": str(self.code),
                "output": str(self.output),
                "traceback": str(self.traceback),
                "snapshot": self.snapshot,
            }
            ticket_storage = TicketStorage(db=request.tickets_db)
            ticket_storage.store(request, request.uuid.split("/", 1)[1], d)
            cmd_opts = global_settings.cmd_options
            if cmd_opts and cmd_opts.errors_to_console:
                logger.error(self.traceback)
            return request.uuid
        except:
            logger.error(self.traceback)
            return None

    def load(self, request, app, ticket_id):
        """
        Loads a logged exception.
        """
        ticket_storage = TicketStorage(db=request.tickets_db)
        d = ticket_storage.load(request, app, ticket_id)

        self.layer = d.get("layer")
        self.code = d.get("code")
        self.output = d.get("output")
        self.traceback = d.get("traceback")
        self.snapshot = d.get("snapshot")

    def __str__(self):
        # safely show an useful message to the user
        return (
            self.output.decode("utf8")
            if isinstance(self.output, bytes)
            else str(self.output)
        )


def compile2(code, layer):
    return compile(code, layer, "exec")


def restricted(ccode, environment=None, layer="Unknown", scode=None):
    """
    Runs code in environment and returns the output. If an exception occurs
    in code it raises a RestrictedError containing the traceback. Layer is
    passed to RestrictedError to identify where the error occurred.
    """
    if environment is None:
        environment = {}
    environment["__file__"] = layer
    environment["__name__"] = "__restricted__"
    try:
        exec(ccode, environment)
    except HTTP:
        raise
    except RestrictedError:
        # do not encapsulate (obfuscate) the original RestrictedError
        raise
    except Exception as error:
        # extract the exception type and value (used as output message)
        etype, evalue, tb = sys.exc_info()
        # XXX Show exception in Wing IDE if running in debugger
        if __debug__ and "WINGDB_ACTIVE" in os.environ:
            sys.excepthook(etype, evalue, tb)
        del tb
        output = "%s %s" % (etype, evalue)
        # Save source code in ticket when available
        scode = scode if scode else ccode
        raise RestrictedError(layer, scode, output, environment)


def snapshot(info=None, context=5, code=None, environment=None):
    """Return a dict describing a given traceback (based on cgitb.text)."""
    import inspect
    import pydoc
    import time

    # if no exception info given, get current:
    etype, evalue, etb = info or sys.exc_info()

    if isinstance(etype, type):
        etype = etype.__name__

    # create a snapshot dict with some basic information
    s = {}
    s["pyver"] = (
        "Python "
        + sys.version.split()[0]
        + ": "
        + sys.executable
        + " (prefix: %s)" % sys.prefix
    )
    s["date"] = time.ctime(time.time())

    # start to process frames
    records = inspect.getinnerframes(etb, context)
    del etb  # Prevent circular references that would cause memory leaks
    s["frames"] = []
    for frame, file, lnum, func, lines, index in records:
        file = file and os.path.abspath(file) or "?"
        args, varargs, varkw, locals = inspect.getargvalues(frame)
        call = ""
        if func != "?":
            call = inspect.formatargvalues(
                args,
                varargs,
                varkw,
                locals,
                formatvalue=lambda value: "=" + pydoc.text.repr(value),
            )

        # basic frame information
        f = {"file": file, "func": func, "call": call, "lines": {}, "lnum": lnum}

        # if it is a view, replace with generated code
        if file.endswith("html"):
            lmin = lnum > context and (lnum - context) or 0
            lmax = lnum + context
            lines = code.split("\n")[lmin:lmax]
            index = min(context, lnum) - 1

        if index is not None:
            i = lnum - index
            for line in lines:
                f["lines"][i] = line.rstrip()
                i += 1

        # dump all local variables in this frame
        f["dump"] = {}
        for name, value in locals.items():
            f["dump"][name] = pydoc.text.repr(value)

        s["frames"].append(f)

    # add exception type, value and attributes
    s["etype"] = str(etype)
    s["evalue"] = str(evalue)
    s["exception"] = {}
    if isinstance(evalue, BaseException):
        for name in dir(evalue):
            value = pydoc.text.repr(getattr(evalue, name))
            s["exception"][name] = value

    # add all local values (of last frame) to the snapshot
    s["locals"] = {}
    for name, value in locals.items():
        s["locals"][name] = pydoc.text.repr(value)

    # add web2py environment variables
    for k, v in environment.items():
        if k in ("request", "response", "session"):
            s[k] = XML(str(BEAUTIFY(v)))

    return s