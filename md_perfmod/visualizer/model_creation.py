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
    _, tmp_file = tempfile.mkstemp()
    params = Parameters(vars=variables, metric=metric, repeat=repeat, fixed=fixed, experiment='exp', file_in=file,
                        file_out=tmp_file)
    perform_conversion(params)
    return tmp_file


def extrap_one_param(file_in, file_out):
    subprocess.check_call(['extrap-modeler', 'input', file_in, '-o', file_out], timeout=30)
    model_summary = subprocess.check_output(['extrap-print', file_out]).decode("utf-8")

    return re.search(r'model: (.+)\n', model_summary).group(1)


def extrap_two_param(file_in, file_out):
    subprocess.check_call(['exp_two_param', file_in, file_out], timeout=30)
    with open(file_out) as csv_file:
        reader = csv.reader(csv_file, delimiter=',')
        model_summary = [row for row in reader][1][2]

    print(model_summary)

    return re.search(r'\+ (.+)', model_summary).group(1)


def create(file, variables, metric, repeat, compare, compare_vals, fixed):
    def get_model(cmp_dict=None):
        try:
            f = fixed.copy()
            if cmp_dict is not None:
                f.update(cmp_dict)
            tmp_file_in = convert(file, variables, metric, repeat, f)

            _, tmp_file_out = tempfile.mkstemp()

            if len(variables) == 1:
                return extrap_one_param(tmp_file_in, tmp_file_out)
            elif len(variables) == 2:
                return extrap_two_param(tmp_file_in, tmp_file_out)
            else:
                raise ValueError("Parameters with more than 2 parameters are currently not supported")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None

    if compare is None:
        # create single model
        m = get_model()
        if m is None:
            return []
        return [Model(m, variables)]
    else:
        # create multiple models
        def get_model_comp(compare_val):
            cmp = {compare: compare_val}
            model_str = get_model(cmp)
            if model_str is None:
                return None
            return Model(model_str, variables, name=compare_val)

        with Pool(multiprocessing.cpu_count()) as p:
            models = p.map(get_model_comp, compare_vals)
            return list(filter(lambda x: x is not None, models))
