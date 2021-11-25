from typing import Any, Type
import sys

if sys.version_info >= (3, 8):
    from typing import get_args
else:
    # from typing import GenericAlias, _GenericAlias, _is_param_expr
    # import types
    # import collections

    def get_args(tp):
        return tp.__args__
        # if isinstance(tp, (_GenericAlias, GenericAlias)):
        #     res = tp.__args__
        #     if (tp.__origin__ is collections.abc.Callable
        #             and not (len(res) == 2 and _is_param_expr(res[0]))):
        #         res = (list(res[:-1]), res[-1])
        #     return res
        # if isinstance(tp, types.UnionType):
        #     return tp.__args__
        # return ()


def unwrap_iterable(t: Type) -> Type:
    'Unwrap an iterable type'
    if t == Any:
        return Any
    a = get_args(t)
    assert len(a) == 1
    return a[0]
