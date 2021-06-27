import ast
from typing import Union, cast

from .object_stream import ObjectStream
from .util_ast import as_ast, function_call


def Range(lower_bound: Union[str, int, ast.AST], upper_bound: Union[str, int, ast.AST]) \
        -> ObjectStream:
    r"""
    Given the lower and upper bound return an object with the range of numbers, similar to python
    range

    Arguments:

        lower_bound     The start of the range
        upper_bound     The end of the range

    Return:

        A new ObjectStream that contains the range of numbers

    """

    return ObjectStream(function_call("Range",
                                      [cast(ast.AST, as_ast(lower_bound)),
                                       cast(ast.AST, as_ast(upper_bound))]))
