"""Helper functions to get absolute paths"""
import os
from os import path


def abs_folder(file=None):
    if file is None:
        return abs_path(os.getcwd())
    return path.dirname(abs_path(file))


def abs_path(file):
    return path.realpath(path.expandvars(path.expanduser(file)))
