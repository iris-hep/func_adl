from typing import Any, Type
import sys

if sys.version_info >= (3, 8):
    from typing import get_args
else:  # pragma: no cover
    def get_args(tp):
        'Return arguments - this is done very simply and will fail ugly'
        return tp.__args__


def unwrap_iterable(t: Type) -> Type:
    'Unwrap an iterable type'
    if t == Any:
        return Any
    a = get_args(t)
    assert len(a) == 1, f'Coding error - expected iterable type with a parameter, got {t}'
    return a[0]
