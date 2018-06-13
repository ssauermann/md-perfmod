import math

from md_perfmod.models import model


def test_notation_fix():
    assert '1+2*x^2' == model.notation_fix('1+2*x^2')
    assert 'x+a^0.7' == model.notation_fix('x^1+a^0.7')
    assert '(log2(x))^2' == model.notation_fix('log2^2(x)')
    assert 'log2(x)' == model.notation_fix('log2^1(x)')


def test_evaluate():
    m = model.Model('2*x', ['x'])
    result = m.evaluate(2.5)
    assert math.isclose(result, 5)


def test_evaluate2():
    m = model.Model('b*log2^2(a)', ['a', 'b'])
    result = m.evaluate(8, 2)
    assert math.isclose(result, 18)


def test_evaluate3():
    m = model.Model('1', ['a'])
    result = m.evaluate(8)
    assert math.isclose(result, 1)


def test_integrate():
    m = model.Model('2*x', ['x'])
    result = m.integrate((0, 3))
    assert math.isclose(result, 9)


def test_integrate2():
    m = model.Model('x*y', ['x', 'y'])
    result = m.integrate((0, 1), (0, 1))
    assert math.isclose(result, 1/4)
