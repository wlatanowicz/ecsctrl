import os


def get_file_path(name):
    return os.path.join(os.path.dirname(__file__), name)
