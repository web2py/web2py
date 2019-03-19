import logging
import os
import sys

try:
    if sys.version_info[0] == 2:
        import Tkinter as tkinter
    else:
        import tkinter
except ImportError:
    tkinter = None


class MessageBoxHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)

    def emit(self, record):
        if tkinter:
            msg = self.format(record)
            root = tkinter.Tk()
            root.wm_title("web2py logger message")
            text = tkinter.Text()
            text["height"] = 12
            text.insert(0.1, msg)
            text.pack()
            button = tkinter.Button(root, text="OK", command=root.destroy)
            button.pack()
            root.mainloop()


class NotifySendHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)

    def emit(self, record):
        if tkinter:
            msg = self.format(record)
            os.system("notify-send '%s'" % msg)
