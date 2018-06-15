"""Creating models with extrap"""
import csv
import multiprocessing
import subprocess

import re
import tempfile
from pathos.multiprocessing import ProcessPool as Pool

from md_perfmod.csv2extrap import perform_conversion, Parameters
from md_perfmod.models.model import Model


def convert(file, variables, metric, repeat, fixed):
    """
    Convert a csv file to extrap input
    :param file: csv file
    :param variables: list of variable columns
    :param metric: metric column
    :param repeat: repeat column or None
    :param fixed: dictionary of column:value to fix
    :return: path to the created extrap input file
    """
    _, tmp_file = tempfile.mkstemp()
    params = Parameters(vars=variables, metric=metric, repeat=repeat, fixed=fixed, experiment='exp', file_in=file,
                        file_out=tmp_file)
    perform_conversion(params)
    return tmp_file


def extrap_one_param(file_in):
    """
    Uses extrap to create a one parameter model
    :param file_in: extrap input
    :return: model as string, adj r^2
    """
    _, file_out = tempfile.mkstemp()

    subprocess.check_call(['extrap-modeler', 'input', file_in, '-o', file_out], timeout=30)
    model_summary = subprocess.check_output(['extrap-print', file_out]).decode("utf-8")

    model_str = re.search(r'model: (.+)\n', model_summary).group(1)
    r2 = re.search(r'Adjusted R\^2: (.+)\n', model_summary).group(1)

    return model_str, float(r2)


def extrap_two_param(file_in):
    """
    Uses extrap to create a two parameter model
    :param file_in: extrap input
    :return: model as string, adj r^2
    """
    _, file_out = tempfile.mkstemp()
    subprocess.check_call(['exp_two_param', file_in, file_out], timeout=30)
    with open(file_out) as csv_file:
        reader = csv.reader(csv_file, delimiter=',')
        model_summary = [row for row in reader][1]

    model_str = re.search(r'\+ (.+)', model_summary[2]).group(1)
    r2 = model_summary[4]

    return model_str, float(r2)


def create(file, variables, metric, repeat, compare, compare_values, fixed):
    """
    Creates a model with extrap
    :param file: csv file
    :param variables: list of variable columns
    :param metric: metric column
    :param repeat: repeat column or None
    :param compare: compare column
    :param compare_values: unique values of compare column
    :param fixed: dictionary of column:value to fix
    :return: Model
    """
    def get_model(cmp_dict=None):
        try:
            f = fixed.copy()
            if cmp_dict is not None:
                f.update(cmp_dict)
            tmp_file_in = convert(file, variables, metric, repeat, f)

            if len(variables) == 1:
                return extrap_one_param(tmp_file_in)
            elif len(variables) == 2:
                return extrap_two_param(tmp_file_in)
            else:
                raise ValueError("Parameters with more than 2 parameters are currently not supported")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None

    if compare is None:
        # create single model
        m, r2 = get_model()
        if m is None:
            return []
        return [Model(m, variables, adj_r2=r2)]
    else:
        # create multiple models
        def get_model_comp(compare_val):
            cmp = {compare: compare_val}
            model_str, adj_r2 = get_model(cmp)
            if model_str is None:
                return None
            return Model(model_str, variables, name=compare_val, adj_r2=adj_r2)

        with Pool(multiprocessing.cpu_count()) as p:
            models = p.map(get_model_comp, compare_values)
            return list(filter(lambda x: x is not None, models))
