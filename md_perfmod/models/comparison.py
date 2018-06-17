"""Compare combined models with models of higher dimensions"""

from itertools import product

import numpy as np

from .model import Model


def combine(model_a, model_b, combined_name=None):
    """
    Combines two models into one. The variables are in the order: model_a, model_b with duplicates removed
    :param combined_name: Name of the combined model
    :param model_a: First model
    :param model_b: Second model
    :return: Combined model
    """
    new_model_str = "(%s)*(%s)" % (model_a.model_str, model_b.model_str)
    combined_vars = [] + model_a.variables + list(filter(lambda v: v not in model_a.variables, model_b.variables))
    m = Model(new_model_str, combined_vars)
    m.name = combined_name
    return m


def find_best(list_of_models, point, best=min):
    evaluated = map(lambda x: x.evaluate(*point), list_of_models)
    return best(zip(list_of_models, evaluated), key=lambda x: x[1])


def distance_to_real_best(high_dim_models, combined_models, point, *, best=min, distance_norm=lambda x, y: abs(x - y)):
    best_cm, _ = find_best(combined_models, point, best)
    matching_hdm = next(m for m in high_dim_models if m.name == best_cm.name)
    best_hdm, metric_best = find_best(high_dim_models, point, best)
    if matching_hdm.name == best_hdm:
        return 0
    metric_matching = matching_hdm.evaluate(*point)
    return distance_norm(metric_best, metric_matching)


def sample_points(bounds, n_samples):
    return product(*list(map(lambda bound: np.linspace(bound[0], bound[1], n_samples), bounds)))


def calculate_error(high_dim_models, combined_models, *bounds, n_samples=53, best=min,
                    distance_norm=lambda x, y: abs(x - y), rel=False):
    x = sample_points(bounds, n_samples)

    def distance_fun(p):
        return distance_to_real_best(high_dim_models, combined_models, p, best=best, distance_norm=distance_norm)

    errors = list(map(distance_fun, x))
    if not rel:
        return sum(errors), errors.count(0), min(errors), max(errors)
    else:
        n = (n_samples * n_samples)
        return sum(errors) / n, errors.count(0) / n, min(errors), max(errors)
