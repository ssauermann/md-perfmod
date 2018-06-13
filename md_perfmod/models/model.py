"""Class for an extrap performance model"""
from collections import OrderedDict

import cexprtk
import re

# 1. group: function, 2. group exponent, 4. group argument
#  matches word^float(any) e.g. log2^2(2*x)
fix_regex = re.compile(r'(\w+)\^([-+]?\d*\.?\d+([eE][-+]?\d+)?)(\([^(]*?\))')

# 1. group: base
#  matches word with exponent of 1 e.g. x^1
fix_regex_simplify = re.compile(r'(\w+)\^1(?![\d.])')


def notation_fix(model):
    """
    Replaces function^exponent(x) notation with (function(x))^exponent so the parser works.
    Also removes unnecessary '1' exponents.
    :param model: Model string representation
    :return: Fixed string representation
    """
    tmp = fix_regex_simplify.sub(r'\1', model)  # remove exponent 1
    return fix_regex.sub(tmp, r'(\1\4)^\2')  # replacement with (word(any))^float


class Model:
    def __init__(self, model_str, variables):
        """
        Parses a model expression and prepares it for evaluation
        :param model_str: Expression as string
        :param variables: Variable names that will be replaced with values when evaluating the model
        """
        self.model_str = notation_fix(model_str)
        self.variables = OrderedDict(map(lambda x: (x, 0), variables))  # dict of variables with default value 0

        st = cexprtk.Symbol_Table(self.variables, add_constants=True)
        self.expression = cexprtk.Expression(self.model_str, st)

    def __str__(self):
        return self.model_str

    def evaluate(self, values):
        """
        Evaluate the model at the given position
        :param values: Values for the variables of the model in the same order as the variable names
        :return:
        """
        # assign values to variables; note that the dictionary is ordered
        for k, v in zip(self.variables.keys(), values):
            self.variables[k] = v
        return self.expression()
