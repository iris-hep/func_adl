from typing import Any, Iterable

from func_adl.util_types import unwrap_iterable


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
