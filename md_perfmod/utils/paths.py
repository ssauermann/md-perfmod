"""Helper functions to get absolute paths"""
from os import path


def abs_folder(file=__file__):
    return path.dirname(abs_path(file))


def abs_path(file):
    return path.realpath(path.expandvars(path.expanduser(file)))
