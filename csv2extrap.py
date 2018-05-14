import pandas as pd
from collections import namedtuple


def read_params():
    """
    Read the input parameters required to determine which CSV column is the repeat count, the metric to use and the
    variables of the model. As well as the path of the input and output files.
    :return: Named parameter tuple
    """

    Parameters = namedtuple('Parameters', 'vars metric repeat file_in file_out')

    # TODO Argument parsing
    variables = ['density', 'cutoff']
    metric = 'time'
    repeat = 'repeat'
    file_in = 'ls1-bench1.csv'
    file_out = 'ls1-bench1.txt'

    return Parameters(variables, metric, repeat, file_in, file_out)


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

    print(mapping)


if __name__ == "__main__":
    main()
