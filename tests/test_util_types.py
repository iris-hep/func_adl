from typing import Any, Iterable, TypeVar

from func_adl.util_types import get_inherited, is_iterable, unwrap_iterable


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


def test_inherrited_generic():
    T = TypeVar('T')

    class bogus(Iterable[T]):
        pass

    myc = bogus[int]

    assert unwrap_iterable(myc) == int


def test_non_iterable():
    assert unwrap_iterable(int) == Any


def test_non_iterable_obj():
    class bogus:
        pass

    assert unwrap_iterable(bogus) == Any


def test_get_inherited_int():
    assert get_inherited(int) == Any


def test_get_inherited_generic():
    T = TypeVar('T')

    class bogus(Iterable[T]):
        pass

    myc = bogus[int]

    assert get_inherited(myc) == Iterable[int]
