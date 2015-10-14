# -*- coding: utf-8 -*-
class I8Error(Exception):
    """Base class for all errors.
    """
    def __init__(self, msg, prefix):
        Exception.__init__(self, prefix + ": error: " + msg)

def version():
    try:
        import pkg_resources
        return pkg_resources.get_distribution("i8c").version
    except: # pragma: no cover
        # This block is excluded from coverage because while
        # we could test it (by hiding the egg-info somehow?)
        # it seems like a lot of effort for very little gain.
        return "UNKNOWN"
