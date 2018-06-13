"""Class for an extrap performance model"""

import cexprtk
import numpy as np
import re
from scipy.integrate import simps

# 1. group: function, 2. group exponent, 4. group argument
#  matches word^float(any) e.g. log2^2(2*x)
fix_regex = re.compile(r'(\w+)\^([-+]?\d*\.?\d+([eE][-+]?\d+)?)(\([^(]*?\))')

# 1. group: base
#  matches word with exponent of 1 e.g. x^1
fix_regex_simplify = re.compile(r'(\w+)\^1(?![\d.])')


def notation_fix(expression):
    """
    Replaces function^exponent(x) notation with (function(x))^exponent so the parser works.
    Also removes unnecessary '1' exponents.
    :param expression: Model string representation
    :return: Fixed string representation
    """
    tmp = fix_regex_simplify.sub(r'\1', expression)  # remove exponent 1
    return fix_regex.sub(r'(\1\4)^\2', tmp)  # replacement with (word(any))^float


class Model:
    def __init__(self, model_str, variables):
        """
        Parses a model expression and prepares it for evaluation
        :param model_str: Expression as string
        :param variables: Variable names that will be replaced with values when evaluating the model
        """
        self.model_str = notation_fix(model_str)
        self.variables = variables
        var_dict = dict(map(lambda x: (x, 0), variables))  # dict of variables with default value 0

        self.symbols = cexprtk.Symbol_Table(var_dict, add_constants=True)
        self.expression = cexprtk.Expression(self.model_str, self.symbols)

    def __str__(self):
        return self.model_str

    def evaluate(self, *values):
        """
        Evaluate the model at the given position
        :param values: Values for the variables of the model in the same order as the variable names
        :return:
        """
        if len(values) != len(self.variables):
            raise ValueError('Must provide a value for each variable')
        # assign values to variables; note that the dictionary is ordered
        for k, v in zip(self.variables, values):
            self.symbols.variables[k] = v
        return self.expression()

    def integrate(self, *bounds):
        """
        Integrate the model in the given bounds
        :param bounds: (low, high) tuples defining the integration bounds for each dimension
        :return: Area below the model curve
        """
        dimensions = len(bounds)
        print(dimensions)
        x = list(map(lambda bound: np.linspace(bound[0], bound[1], 3), bounds))
        print("x", x)
        x_matrix = np.stack(np.meshgrid(*x), -1).reshape(-1, dimensions)
        print("X", x_matrix)
        samples = np.vectorize(self.evaluate)(x)
        print("Samples", samples)

        for d in range(dimensions):
            print("Xd", x[d])
            samples = simps(samples, x[d])

        return samples
