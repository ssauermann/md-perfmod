import pandas as pd
from collections import namedtuple


def read_params():
    """
    Read the input parameters required to determine which CSV column is the repeat count, the metric to use and the
    variables of the model. As well as the path of the input and output files.
    :return: Named parameter tuple
    """

    Parameters = namedtuple('Parameters', 'vars metric repeat file_in file_out experiment')

    # TODO Argument parsing
    variables = ['cutoff']
    metric = 'time'
    repeat = 'repeat'
    file_in = 'ls1-bench1.csv'
    file_out = 'ls1-bench1.txt'
    exp_name = 'experiment'

    return Parameters(variables, metric, repeat, file_in, file_out, exp_name)


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


def main():
    params = read_params()

    # Read CSV into a data frame
    data = pd.read_csv(params.file_in)

    # Select columns containing variables, metric and repeat count
    # Drop duplicate entries # TODO Selection which of the duplicates to keep
    # Sort by the parameters and the repeat count
    selected_data = data[params.vars + [params.metric] + [params.repeat]] \
        .drop_duplicates(subset=params.vars + [params.repeat]) \
        .sort_values(params.vars + [params.repeat])

    # Convert the selected data to a map of points to a list of metrics
    # A point is a tuple of variable instances e.g. (2.0, 1.2) for variables (a, b)
    # The list of metrics consists of the repeated measurements
    mapping = {}
    for row in selected_data.values:
        point = tuple(row[:-2])  # the vars
        if point not in mapping.keys():
            mapping[point] = []
        mapping[point].append(row[-2])  # the metric

    write_extrap(mapping, params)

    print("Conversion completed!")


if __name__ == "__main__":
    main()
