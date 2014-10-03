# -*- coding: utf-8 -*-
import os

from ._compat import exists
from ._globals import GLOBAL_LOCKER, THREAD_LOCAL
from .helpers.classes import UseDatabaseStoredFile

class ConnectionPool(object):

    POOLS = {}
    check_active_connection = True

    @staticmethod
    def set_folder(folder):
        THREAD_LOCAL.folder = folder

    # ## this allows gluon to commit/rollback all dbs in this thread

    def close(self,action='commit',really=True):
        if action:
            if callable(action):
                action(self)
            else:
                getattr(self, action)()
        # ## if you want pools, recycle this connection
        if self.pool_size:
            GLOBAL_LOCKER.acquire()
            pool = ConnectionPool.POOLS[self.uri]
            if len(pool) < self.pool_size:
                pool.append(self.connection)
                really = False
            GLOBAL_LOCKER.release()
        if really:
            self.close_connection()
        self.connection = None

    @staticmethod
    def close_all_instances(action):
        """ to close cleanly databases in a multithreaded environment """
        dbs = getattr(THREAD_LOCAL,'db_instances',{}).items()
        for db_uid, db_group in dbs:
            for db in db_group:
                if hasattr(db,'_adapter'):
                    db._adapter.close(action)
        getattr(THREAD_LOCAL,'db_instances',{}).clear()
        getattr(THREAD_LOCAL,'db_instances_zombie',{}).clear()
        if callable(action):
            action(None)
        return

    def find_or_make_work_folder(self):
        #this actually does not make the folder. it has to be there
        self.folder = getattr(THREAD_LOCAL,'folder','')

        if (os.path.isabs(self.folder) and
            isinstance(self, UseDatabaseStoredFile) and
            self.folder.startswith(os.getcwd())):
            self.folder = os.path.relpath(self.folder, os.getcwd())

        # Creating the folder if it does not exist
        if False and self.folder and not exists(self.folder):
            os.mkdir(self.folder)

    def after_connection_hook(self):
        """Hook for the after_connection parameter"""
        if callable(self._after_connection):
            self._after_connection(self)
        self.after_connection()

    def after_connection(self):
        #this it is supposed to be overloaded by adapters
        pass

    def reconnect(self, f=None, cursor=True):
        """
        Defines: `self.connection` and `self.cursor`
        (if cursor is True)
        if `self.pool_size>0` it will try pull the connection from the pool
        if the connection is not active (closed by db server) it will loop
        if not `self.pool_size` or no active connections in pool makes a new one
        """
        if getattr(self,'connection', None) is not None:
            return
        if f is None:
            f = self.connector

        # if not hasattr(self, "driver") or self.driver is None:
        #     LOGGER.debug("Skipping connection since there's no driver")
        #     return

        if not self.pool_size:
            self.connection = f()
            self.cursor = cursor and self.connection.cursor()
        else:
            uri = self.uri
            POOLS = ConnectionPool.POOLS
            while True:
                GLOBAL_LOCKER.acquire()
                if not uri in POOLS:
                    POOLS[uri] = []
                if POOLS[uri]:
                    self.connection = POOLS[uri].pop()
                    GLOBAL_LOCKER.release()
                    self.cursor = cursor and self.connection.cursor()
                    try:
                        if self.cursor and self.check_active_connection:
                            self.execute('SELECT 1;')
                        break
                    except:
                        pass
                else:
                    GLOBAL_LOCKER.release()
                    self.connection = f()
                    self.cursor = cursor and self.connection.cursor()
                    break
        self.after_connection_hook()
