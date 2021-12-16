from typing import Any, Type
import sys

if sys.version_info >= (3, 8):
    from typing import get_args
else:  # pragma: no cover
    def get_args(tp):
        'Return arguments - this is done very simply and will fail ugly'
        return tp.__args__


def is_iterable(t: Type) -> bool:
    'Is this type iterable?'
    if getattr(t, '_name', None) == 'Iterable':
        return True
    return False


def get_inherited(t: Type) -> Type:
    'Get the inherited type'
    base_classes = getattr(t, '__orig_bases__', None)
    if base_classes is None:
        return Any

    return t.__orig_bases__[0]


def unwrap_iterable(t: Type) -> Type:
    'Unwrap an iterable type'
    # Try to find an iterable in the history somehow
    while (t is not Any) and (not is_iterable(t)):
        t = get_inherited(t)

    if t == Any:
        return Any

    a = get_args(t)
    assert len(a) == 1, f'Coding error - expected iterable type with a parameter, got {t}'
    return a[0]
