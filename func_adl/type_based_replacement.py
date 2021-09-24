from typing import Any, Tuple, TypeVar
from .object_stream import ObjectStream
import ast


T = TypeVar('T')
S = TypeVar('S')


def remap_by_types(o_stream: ObjectStream[T], var_name: str, var_type: Any, a: ast.AST) \
        -> Tuple[ObjectStream[T], ast.AST]:
    return o_stream, a
