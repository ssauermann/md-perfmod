import argparse
import json
from collections import namedtuple

import pandas as pd

from visualizer.model_creation import create

Parameters = namedtuple('Parameters', 'vars fixed metric compare repeat file_in file_out')


def read_params():
    """
    Reads and processes the program arguments and returns them as a named tuple.
    :return: Named parameter tuple
    """

    parser = argparse.ArgumentParser(description='Creates performance models from a CSV file using Extra-P',
                                     epilog='Example of use: python csv2model.py data.csv -v p q -f a=42 b=3.14')

    parser.add_argument('file_in', help="Input file [csv]")
    parser.add_argument('file_out', nargs='?', default='',
                        help='Output file containing the models in a JSON format (will be overwritten) [default: No '
                             'file is written')
    parser.add_argument('-r', '--repeat', default='repeat',
                        help='Column containing the repeat count [default: %(default)s]')
    parser.add_argument('-m', '--metric', default='time',
                        help='Column containing the measurement values [default: %(default)s]')
    parser.add_argument('-v', '--vars', required=True, nargs='+',
                        help='Column names of the variables to use')
    parser.add_argument('-c', '--compare', default=None,  # nargs='+', # TODO support multiple compare columns
                        help='Create a model for each distinct value in this column [default: %(default)s]')
    parser.add_argument('-f', '--fixed', nargs='+',
                        help='Assignments (variable=value) to fix variables, that are not used for model creation, '
                             'to a specific value.\n'
                             'E.g. when measurements for different combinations of (p, q) were performed but a model '
                             'for only p should be created, using the measurements when q was 3.')
    parser.add_argument('--single-measurement', action='store_true',
                        help='Use this flag if your data has no repeated measurements and therefore no repeat column')

    args = parser.parse_args()

    variables = args.vars
    metric = args.metric
    compare = args.compare
    repeat = args.repeat
    file_in = args.file_in
    file_out = args.file_out

    if args.single_measurement:
        repeat = None

    # Convert fixed variables from [key=val, ...] to dictionary
    fixed = {}
    if args.fixed:
        for entry in args.fixed:
            key, val = entry.split("=", 1)
            fixed[key] = val

    params = Parameters(variables, fixed, metric, compare, repeat, file_in, file_out)

    print(params)  # TODO: Nicer display

    return params


def main():
    params = read_params()

    if params.compare is not None:
        data = pd.read_csv(params.file_in)
        compare_values = data[params.compare].unique()
    else:
        compare_values = []

    models = create(params.file_in, params.vars, params.metric, params.repeat,
                    params.compare, compare_values, params.fixed)

    print('Model creation completed!\n')

    print('%-15s%-12s%-s' % ('Identifier', 'Adj.R^2', 'Model'))
    for model in models:
        print('%-15s%-12f%-s' % (model.name, model.adj_r2, model.model_str))

    if params.file_out is not '':
        with open(params.file_out, 'w') as file:
            json.dump(list(map(lambda x: x.serializable(), models)), file, indent=4)


if __name__ == "__main__":
    main()
