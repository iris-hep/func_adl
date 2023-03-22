from typing import Any, Generic, Iterable, TypeVar

import pytest

from func_adl.util_types import (
    _resolve_type,
    build_type_dict_from_type,
    get_class_name,
    get_inherited,
    get_method_and_class,
    is_iterable,
    resolve_type_vars,
    unwrap_iterable,
)


def test_is_iter_int():
    assert not is_iterable(int)


def test_is_iter_iter():
    assert is_iterable(Iterable[int])


def test_is_iter_inherited():
    class bogus(Iterable[int]):
        def other_stuff(self):
            return 5

    assert is_iterable(bogus)


def test_is_iter_inherited_generic():
    R = TypeVar("R")

    class bogus(Iterable[R]):
        def other_stuff(self):
            return 5

    assert is_iterable(bogus[int])


def test_Any():
    assert unwrap_iterable(Any) == Any


def test_iterable():
    assert unwrap_iterable(Iterable[int]) == int


def test_inherrited():
    class bogus(Iterable[float]):
        pass

    assert unwrap_iterable(bogus) == float


def test_inherrited_generic():
    T = TypeVar("T")

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
    T = TypeVar("T")

    class bogus(Iterable[T]):
        pass

    myc = bogus[int]

    assert get_inherited(myc) == Iterable[int]  # type: ignore


def test_get_inherited_two_levels():
    T = TypeVar("T")
    U = TypeVar("U")

    class bogus(Generic[T]):
        pass

    class bogus2(bogus[Iterable[U]]):
        pass

    myc = bogus2[int]
    assert get_inherited(myc) == bogus[Iterable[int]]


def test_get_inherited_generic_twice():
    T = TypeVar("T")

    class bogus(Iterable[T]):
        pass

    myc = bogus[int]
    assert get_inherited(myc) == Iterable[int]  # type: ignore

    myd = bogus[float]
    assert get_inherited(myd) == Iterable[float]  # type: ignore


def test_build_type_int():
    assert build_type_dict_from_type(int) == {}


def test_build_type_generic():
    T = TypeVar("T")

    class bogus(Iterable[T]):
        pass

    myc = bogus[int]

    assert build_type_dict_from_type(myc) == {"T": int}


def test_build_type_at_level():
    T = TypeVar("T")
    U = TypeVar("U")

    class bogus(Generic[T]):
        pass

    class bogus_inher(bogus[Iterable[U]]):
        pass

    myc = bogus_inher[int]

    assert build_type_dict_from_type(myc) == {"U": int}


def test_build_type_at_level_down_one():
    T = TypeVar("T")
    U = TypeVar("U")

    class bogus(Generic[T]):
        pass

    class bogus_inher(bogus[Iterable[U]]):
        pass

    myc = bogus_inher[int]

    assert build_type_dict_from_type(myc, at_class=bogus) == {"T": Iterable[int]}


def test_build_type_at_level_down_one_reversed():
    T = TypeVar("T")
    U = TypeVar("U")

    class bogus(Generic[T]):
        pass

    class bogus_inher(bogus[Iterable[U]]):
        pass

    myc = bogus[int]

    with pytest.raises(TypeError) as e:
        build_type_dict_from_type(myc, at_class=bogus_inher)

    assert "bogus[" in str(e.value)


def test_resolve_type_int():
    assert _resolve_type(int, {}) == int


def test_resolve_type_generic():
    T = TypeVar("T")

    assert _resolve_type(T, {"T": int}) == int


def test_resolve_type_generic_filled():
    assert _resolve_type(Iterable[int], {"T": int}) == Iterable[int]


def test_resolve_type_generic_not_found():
    T = TypeVar("T")

    assert _resolve_type(T, {}) is None


def test_resolve_type_nested():
    T = TypeVar("T")

    assert _resolve_type(Iterable[T], {"T": int}) == Iterable[int]


def test_resolve_type_nested_unknown():
    K = TypeVar("K")

    assert _resolve_type(Iterable[K], {"T": int}) is None


def test_resolve_type_vars():
    T = TypeVar("T")

    class bogus(Iterable[T]):
        pass

    myc = bogus[int]

    assert resolve_type_vars(T, myc) == int


def test_resolve_type_vars_with_no_match():
    T = TypeVar("T")

    class bogus(Iterable[T]):
        pass

    class bogus_inher(bogus[int]):
        pass

    myc = bogus[int]

    assert resolve_type_vars(int, myc, at_class=bogus_inher) == int


def test_resolve_type_vars_not_there_no_match():
    T = TypeVar("T")

    class bogus(Iterable[T]):
        pass

    class bogus_inher(bogus[int]):
        pass

    myc = bogus[int]

    assert resolve_type_vars(T, myc, at_class=bogus_inher) is None


def test_get_name_simple():
    assert get_class_name(int) == "int"


def test_get_name_obj():
    class bogus:
        pass

    assert get_class_name(bogus) == "bogus"


def test_get_name_template():
    assert get_class_name(Iterable[int]) == "Iterable[int]"


def test_get_method_and_class_not_there():
    class bogus:
        pass

    assert get_method_and_class(bogus, "fork") is None


def test_get_method_and_class_easy():
    class bogus:
        def fork(self):
            pass

    assert get_method_and_class(bogus, "fork") == (bogus, bogus.fork)


def test_get_method_and_class_inherrited():
    class bogus_1:
        def fork(self):
            pass

    class bogus_2(bogus_1):
        pass

    assert get_method_and_class(bogus_2, "fork") == (bogus_1, bogus_1.fork)


def test_get_method_and_class_inherrited_override():
    class bogus_1:
        def fork(self):
            pass

    class bogus_2(bogus_1):
        def __init__(self):
            self.i = 0

        def fork(self):
            self.i = self.i + 1

    assert get_method_and_class(bogus_2, "fork") == (bogus_2, bogus_2.fork)


def test_get_method_and_class_inherrited_template():
    T = TypeVar("T")

    class bogus_1(Generic[T]):
        def fork(self) -> T:
            ...

    class bogus_2(bogus_1[int]):
        pass

    assert get_method_and_class(bogus_2, "fork") == (bogus_1, bogus_1.fork)


def test_get_method_and_class_iterable():
    class bogus:
        def fork(self):
            ...

    assert get_method_and_class(Iterable[bogus], "fork") is None


def test_get_method_and_class_Any():
    assert get_method_and_class(Any, "fork") is None
