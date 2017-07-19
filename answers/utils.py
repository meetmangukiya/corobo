import os

def get_abs_path(path):
    """
    Returns absolute path for paths wrt to this module.
    """
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
