import argparse
from collections import namedtuple

import numpy as np
import os
import pandas as pd


def read_params():
    """
    Read the input parameters required to determine which CSV column is the repeat count, the metric to use and the
    variables of the model. As well as the path of the input and output files.
    :return: Named parameter tuple
    """

    Parameters = namedtuple('Parameters', 'vars fixed metric repeat file_in file_out experiment')

    parser = argparse.ArgumentParser(description='Convert a CSV file containing performance measurements'
                                                 ' to a input file for Extra-P')

    parser.add_argument('file_in', help="Input file [csv]")
    parser.add_argument('file_out', nargs='?', default='', help='Output file [extra-p text] (will be overwritten)')
    parser.add_argument('-n', '--name', default='experiment', help='Name of the experiment for the output')
    parser.add_argument('-r', '--repeat', default='repeat', help='Column containing the repeat count')
    parser.add_argument('-m', '--metric', default='time', help='Column containing the measurement value')
    parser.add_argument('-v', '--vars', required=True, nargs='+', help='Column names of the variables to use')
    parser.add_argument('-f', '--fixed', nargs='+', help='TODO')  # TODO Help text + update method documentation

    args = parser.parse_args()

    variables = args.vars
    metric = args.metric
    repeat = args.repeat
    file_in = args.file_in
    file_out = args.file_out
    exp_name = args.name

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
            fixed[key] = float(val)

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
        file.write('\n')
        write('EXPERIMENT', [params.experiment])
        write('METRIC', [params.metric])
        file.write('\n')
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
        selected_data = data[np.isclose(data[param], val)]
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


def main():
    params = read_params()

    # Read CSV into a data frame
    data = pd.read_csv(params.file_in)

    mapping = conversion(data, params.vars, params.fixed, params.metric, params.repeat)

    write_extrap(mapping, params)

    print("Conversion completed!")


if __name__ == "__main__":
    main()
