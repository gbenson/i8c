import sys

class Logger(object):
    def __init__(self):
        self.enabled = False

    def disable(self):
        self.enabled = False

    def enable(self):
        self.enabled = True

    def __call__(self, msg):
        if self.enabled:
            sys.stderr.write(msg)

loggers = {}

def debug_printer_for(module):
    global loggers
    faculty = module.split(".")[-1]
    logger = loggers.get(faculty, None)
    if logger is None:
        logger = loggers[faculty] = Logger()
    return logger
