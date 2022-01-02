from typing import Any, Iterable

from func_adl.util_types import is_iterable, unwrap_iterable


def test_is_iter_int():
    assert not is_iterable(int)


def test_is_iter_iter():
    assert is_iterable(Iterable[int])


def test_is_iter_inherited():

    class bogus (Iterable[int]):
        def other_stuff(self):
            return 5

    assert is_iterable(bogus)


def test_Any():
    assert unwrap_iterable(Any) == Any


def test_iterable():
    assert unwrap_iterable(Iterable[int]) == int


def test_inherrited():
    class bogus(Iterable[float]):
        pass

    assert unwrap_iterable(bogus) == float


def test_non_iterable():
    assert unwrap_iterable(int) == Any


def test_non_iterable_obj():
    class bogus:
        pass

    assert unwrap_iterable(bogus) == Any
