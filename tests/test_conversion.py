import csv2extrap as cv
import pandas as pd
import numpy as np


class TestConversion(object):

    def test_conversion_simple(self):
        data = np.array([[1, 10, 0],
                         [2, 20, 0],
                         [3, 30, 0]])
        columns = ['p', 'time', 'repeat']
        df = pd.DataFrame(data, columns=columns)
        result = cv.conversion(df, ['p'], {}, 'time', 'repeat')
        assert result[tuple([1])] == [10]
        assert result[tuple([2])] == [20]
        assert result[tuple([3])] == [30]
