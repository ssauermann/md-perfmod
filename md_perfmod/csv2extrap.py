import argparse
from collections import namedtuple

import numpy as np
import os
import pandas as pd

Parameters = namedtuple('Parameters', 'vars fixed metric repeat file_in file_out experiment')


def read_params():
    """
    Reads and processes the program arguments and returns them as a named tuple.
    :return: Named parameter tuple
    """

    parser = argparse.ArgumentParser(description='Converts a CSV file containing performance measurements'
                                                 ' to an input file for Extra-P',
                                     epilog='Example of use: python csv2extrap.py data.csv -v p q -f a=42 b=3.14')

    parser.add_argument('file_in', help="Input file [csv]")
    parser.add_argument('file_out', nargs='?', default='',
                        help='Output file (will be overwritten) [default: FILE_IN with the file ending changed to .txt]')
    parser.add_argument('-n', '--name', default='experiment',
                        help='Name of the experiment for the output [default: %(default)s]')
    parser.add_argument('-r', '--repeat', default='repeat',
                        help='Column containing the repeat count [default: %(default)s]')
    parser.add_argument('-m', '--metric', default='time',
                        help='Column containing the measurement value [default: %(default)s]')
    parser.add_argument('-v', '--vars', required=True, nargs='+',
                        help='Column names of the variables to use')
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
    repeat = args.repeat
    file_in = args.file_in
    file_out = args.file_out
    exp_name = args.name

    if args.single_measurement:
        repeat = None

    # If no output filename was given, just use the input file with a txt ending
    if file_out == '' or file_out.isspace():
        path, ext = os.path.splitext(file_in)
        file_out = path + '.txt'
        if file_out == file_in:
            file_out += '.extrap'  # or with .txt.extrap if the input file has a txt ending already

    # Convert fixed variables from [key=val, ...] to dictionary
    fixed = {}
    if args.fixed:
        for entry in args.fixed:
            key, val = entry.split("=", 1)
            fixed[key] = val

    params = Parameters(variables, fixed, metric, repeat, file_in, file_out, exp_name)

    print(params)  # TODO: Nicer display

    return params


def write_extrap(mapping, params):
    """
    Writes a mapping to the output file in the extrap format.
    :param mapping: Point to metrics mapping to write
    :param params: Parameters containing the output file and other settings
    """
    with open(params.file_out, 'w') as file:
        def write(header, values, converter=str):
            """
            Write a line to the result file
            :param header: Line prefix
            :param values: List of values to write
            :param converter: Function to apply to every value before printing
            """
            file.write(header + ' ' + ' '.join(map(converter, values)) + '\n')

        def point_converter(p):
            """
            Converts a point to its string representation
            :param p: Point
            :return: String representation
            """
            if len(p) > 1:
                return '( ' + ' '.join([str(f) for f in p]) + ' )'
            else:
                return str(p[0])

        # Sorting the points by each element
        points = sorted(mapping.keys())

        # Write extrap file format
        write('PARAMETER', params.vars)
        write('POINTS', points, point_converter)
        write('METRIC', [params.metric])
        if len(params.vars) > 1:
            write('EXPERIMENT', [params.experiment])
        else:
            write('REGION', [params.experiment])
        for point in points:
            write('DATA', mapping[point])


def conversion(data, var, fixed, metric, repeat):
    """
    Converts the given data frame to a point to metric mapping.
    :param data: Data frame to convert
    :param var: List of variables to use as parameters
    :param fixed: Dict of unused variables to keep fixed at a specific value
    :param metric: The metric to use
    :param repeat: The column containing the repeat count
    :return: Point to metric mapping
    """
    # Parameter validation
    if repeat is not None and repeat not in data.columns:
        raise ValueError('Repeat column `%s` does not exist.' % repeat)
    if metric not in data.columns:
        raise ValueError('Metric column `%s` does not exist.' % metric)
    for v in var:
        if v not in data.columns:
            raise ValueError('Variable column `%s` does not exist.' % v)
    for f in fixed.keys():
        if f not in data.columns:
            raise ValueError('Variable column `%s` does not exist and therefore can not be fixed.' % f)

    # Select rows with fixed parameters
    selected_data = data.sort_values(list(data.columns))
    for param, val in fixed.items():
        if param in var:
            raise ValueError("Parameter `%s` can not be fixed, because it is used as a variable." % param)
        try:
            selected_data = selected_data[np.isclose(selected_data[param], float(val))]
        except ValueError:
            selected_data = selected_data[selected_data[param] == val]
        if len(selected_data) == 0:
            raise ValueError("Parameter `%s` can not be fixed to `%s`." % (param, val))

    # Create list of columns to use
    columns_no_metrics = [] + var
    columns_all = [] + var + [metric]
    if repeat is not None:
        columns_no_metrics += [repeat]
        columns_all += [repeat]

    # Select columns containing variables, metric and repeat count
    # Drop duplicate entries
    # Sort by the parameters and the repeat count
    selected_data = selected_data[columns_all] \
        .drop_duplicates(subset=columns_no_metrics) \
        .sort_values(columns_no_metrics)

    # Convert the selected data to a map of points to a list of metrics
    # A point is a tuple of variable instances e.g. (2.0, 1.2) for variables (a, b)
    # The list of metrics consists of the repeated measurements
    mapping = {}
    for row in selected_data.values:
        point = tuple(row[:len(var)])  # the vars
        if point not in mapping.keys():
            mapping[point] = []
        mapping[point].append(row[len(var)])  # the metric

    return mapping


def perform_conversion(params):
    # Read CSV into a data frame
    data = pd.read_csv(params.file_in)

    mapping = conversion(data, params.vars, params.fixed, params.metric, params.repeat)

    write_extrap(mapping, params)


def main():
    perform_conversion(read_params())

    print("Conversion completed!")


if __name__ == "__main__":
    main()
