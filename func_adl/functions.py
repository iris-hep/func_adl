import ast
from typing import Union

from .object_stream import ObjectStream


def Range(
    lower_bound: Union[str, int, ast.AST], upper_bound: Union[str, int, ast.AST]
) -> ObjectStream[int]:
    r"""
    Given the lower and upper bound return an object with the range of numbers, similar to python
    range

    Arguments:

        lower_bound     The start of the range
        upper_bound     The end of the range

    Return:

        A new ObjectStream that contains the range of numbers
    """
    ...
