from typing import Any, Type, get_args


def unwrap_iterable(t: Type) -> Type:
    'Unwrap an iterable type'
    if t == Any:
        return Any
    a = get_args(t)
    assert len(a) == 1
    return a[0]
