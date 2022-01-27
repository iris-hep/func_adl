from typing import Any, Type
import sys

if sys.version_info >= (3, 8):
    from typing import get_args
else:  # pragma: no cover
    def get_args(tp):
        'Return arguments - this is done very simply and will fail ugly'
        return getattr(tp, '__args__', ())


def is_iterable(t: Type) -> bool:
    'Is this type iterable?'
    while (t is not Any) and (not _is_iterable_direct(t)):
        t = get_inherited(t)

    return t is not Any


def _is_iterable_direct(t: Type) -> bool:
    'Is this type iterable?'
    if getattr(t, '_name', None) == 'Iterable':
        return True
    return False


def get_inherited(t: Type) -> Type:
    '''Returns the inherited type of `t`

    Notes:
    * This works for 3.7 forward (but not back!)

    Args:
        t (Type): The type (a class) that we should look at

    Returns:
        Type: The type for an inherited class, or `Any` if none can be found
    '''
    if hasattr(t, '__orig_bases__'):
        base_classes = getattr(t, '__orig_bases__', None)
    elif hasattr(t, '__origin__'):
        base_classes = t.__origin__.__orig_bases__
    else:
        return Any

    r = base_classes[0]  # type: ignore

    g_args = get_args(t)
    if len(g_args) > 0:
        r.__args__ = g_args

    return r


def unwrap_iterable(t: Type) -> Type:
    'Unwrap an iterable type'
    # Try to find an iterable in the history somehow

    while (t is not Any) and (not _is_iterable_direct(t)):
        t = get_inherited(t)

    if t == Any:
        return Any

    a = get_args(t)
    assert len(a) == 1, f'Coding error - expected iterable type with a parameter, got {t}'
    return a[0]
