import numpy as np
import pandas as pd
import pytest

import csv2extrap as cv


class TestConversion(object):
    columns_simple = ['p', 'time', 'repeat']
    data_simple = np.array([[1, 10, 0],
                            [2, 20, 0],
                            [3, 30, 0]])
    df_simple = pd.DataFrame(data_simple, columns=columns_simple)

    columns_repeat = ['p', 'time', 'repeat']
    data_repeat = np.array([[1, 10, 0],
                            [1, 11, 1],
                            [2, 20, 0],
                            [2, 21, 1],
                            [3, 30, 0],
                            [3, 31, 1]])
    df_repeat = pd.DataFrame(data_repeat, columns=columns_repeat)

    columns_complex = ['p', 'q', 'time', 'repeat']
    data_complex = np.array([[1, 1, 110, 0],
                             [2, 1, 210, 0],
                             [3, 1, 310, 0],
                             [1, 2, 120, 0],
                             [2, 2, 220, 0],
                             [3, 2, 320, 0],
                             [1, 3, 130, 0],
                             [2, 3, 230, 0],
                             [3, 3, 330, 0]])
    df_complex = pd.DataFrame(data_complex, columns=columns_complex)

    def test_simple(self):
        df = self.df_simple.copy(deep=True)
        result = cv.conversion(df, ['p'], {}, 'time', 'repeat')
        assert result[(1,)] == [10]
        assert result[(2,)] == [20]
        assert result[(3,)] == [30]

    def test_complex_both_vars(self):
        df = self.df_complex.copy(deep=True)
        result = cv.conversion(df, ['p', 'q'], {}, 'time', 'repeat')
        assert result[(1, 1)] == [110]
        assert result[(1, 2)] == [120]
        assert result[(1, 3)] == [130]
        assert result[(2, 1)] == [210]
        assert result[(2, 2)] == [220]
        assert result[(2, 3)] == [230]
        assert result[(3, 1)] == [310]
        assert result[(3, 2)] == [320]
        assert result[(3, 3)] == [330]

    def test_complex_single_var(self):
        df = self.df_complex.copy(deep=True)
        result = cv.conversion(df, ['q'], {}, 'time', 'repeat')
        # unused variable q should be fixed to smallest value: p = 1
        assert result[(1,)] == [110]
        assert result[(2,)] == [120]
        assert result[(3,)] == [130]

    def test_complex_single_var_fixed(self):
        df = self.df_complex.copy(deep=True)
        result = cv.conversion(df, ['p'], {'q': 2}, 'time', 'repeat')
        assert result[(1,)] == [120]
        assert result[(2,)] == [220]
        assert result[(3,)] == [320]

    def test_fixed_and_var(self):
        df = self.df_complex.copy(deep=True)
        with pytest.raises(ValueError):
            cv.conversion(df, ['q', 'p'], {'p': 2}, 'time', 'repeat')

    def test_fixed_to_nonexistent_value(self):
        df = self.df_complex.copy(deep=True)
        with pytest.raises(ValueError):
            cv.conversion(df, ['p'], {'q': 5}, 'time', 'repeat')

    def test_nonexistent_metric(self):
        df = self.df_simple.copy(deep=True)
        with pytest.raises(ValueError):
            cv.conversion(df, ['p'], {}, 'none', 'repeat')

    def test_repeat(self):
        df = self.df_repeat.copy(deep=True)
        result = cv.conversion(df, ['p'], {}, 'time', 'repeat')
        assert 10 in result[(1,)] and 11 in result[(1,)]
        assert 20 in result[(2,)] and 21 in result[(2,)]
        assert 30 in result[(3,)] and 31 in result[(3,)]

    def test_nonexistent_repeat(self):
        df = self.df_repeat.copy(deep=True)
        with pytest.raises(ValueError):
            cv.conversion(df, ['p'], {}, 'time', 'none')

    def test_no_repeat(self):
        df = self.df_repeat.copy(deep=True)
        result = cv.conversion(df, ['p'], {}, 'time', None)
        assert 10 in result[(1,)] or 11 in result[(1,)]
        assert 20 in result[(2,)] or 21 in result[(2,)]
        assert 30 in result[(3,)] or 31 in result[(3,)]
