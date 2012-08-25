import logging

try:
    import tkMessageBox
except:
    tkMessageBox = None

class MessageBoxHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)

    def emit(self, record):
        if tkMessageBox:
            msg = self.format(record)
            tkMessageBox.showinfo('info1', msg)


