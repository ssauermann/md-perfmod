"""Creating models with extrap"""
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
    print(params)
    perform_conversion(params)
    return tmp_file


def create(file, variables, metric, repeat, compare, compare_vals, fixed):
    def get_model(cmp_dict=None):
        try:
            f = fixed.copy()
            if cmp_dict is not None:
                f.update(cmp_dict)
            tmp_file_in = convert(file, variables, metric, repeat, f)

            _, tmp_file_out = tempfile.mkstemp()
            subprocess.check_call(['extrap-modeler', 'input', tmp_file_in, '-o', tmp_file_out], timeout=30)
            model_summary = subprocess.check_output(['extrap-print', tmp_file_out]).decode("utf-8")

            return re.search(r'model: (.+)\n', model_summary).group(1)
        except subprocess.CalledProcessError:
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
            models = p.map(get_model_comp, compare_vals)  # TODO compare_vals = df[sel_compare].unique()
            return list(filter(lambda x: x is not None, models))
