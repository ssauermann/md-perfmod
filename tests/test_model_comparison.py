import math

from md_perfmod.models import comparison
from md_perfmod.models.model import Model


def test_combine():
    a = Model('2*x', ['x'])
    b = Model('3*y', ['y'])
    c = comparison.combine(a, b)
    assert (c.evaluate(5, 5) == a.evaluate(5) * b.evaluate(5))


def test_calculate_error():
    two_d = [Model('4', ['x', 'y'], 'A'), Model('x+y', ['x', 'y'], 'B')]
    combined_1 = comparison.combine(Model('2', ['x']), Model('2', ['y']), 'A')
    combined_2 = comparison.combine(Model('x', ['x']), Model('y', ['y']), 'B')
    combined = [combined_1, combined_2]
    err, err_c = comparison.calculate_error(two_d, combined, (0, 5), (0, 5), n_samples=3)
    assert math.isclose(err, 2, rel_tol=1e-3)
    assert err_c == 7
    # TODO Verify values by hand


def test_calculate_error2():
    two_d = [Model('4', ['x', 'y'], 'A'), Model('x+y', ['x', 'y'], 'B')]
    err, err_c = comparison.calculate_error(two_d, two_d, (0, 5), (0, 5), n_samples=10)
    assert err == 0
    assert err_c == 100
