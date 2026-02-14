import ast
from abc import ABC
from typing import Any, Optional, Type, TypeVar

from .object_stream import ObjectStream
from .util_ast import function_call

T = TypeVar("T")


class EventDataset(ObjectStream[T], ABC):
    r"""
    A source of event objects (a ROOT file, or a xAOD file). This class
    should be sub-classed with the information about the actual dataset, and
    should never be created on its own.
    """

    def __init__(self, item_type: Type = Any):  # type: ignore
        """
        Should not be called directly. Make sure to initialize this ctor
        or tracking information will be lost.
        """

        # Create the base AST node.
        ed_ast = function_call("EventDataset", [])

        # Safely store a reference to this object
        setattr(ed_ast, "_eds_object", self)

        # Let ObjectStream take care of passing around this AST.
        super().__init__(ed_ast, item_type)

    def __repr__(self):
        return f"'{self.__class__.__name__}'"

    def __str__(self):
        return self.__class__.__name__


def find_EventDataset(a: ast.AST) -> ast.Call:
    r"""
    Given an input query ast, find the EventDataset `ast` and return it.

    Args:
        a:      An AST that represents a query

    Returns:
        The `EventDataset` `ast` at the root of this query. It will not be None.

    Exceptions:
        If there is more than one `EventDataset` found in the query or if there
        is no `EventDataset` at the root of the query, then an exception is thrown.
    """

    class ds_finder(ast.NodeVisitor):
        def __init__(self):
            self.ds: Optional[ast.Call] = None

        def visit_Call(self, node: ast.Call):
            if not isinstance(node.func, ast.Name):
                return self.generic_visit(node)
            if node.func.id != "EventDataset":
                return self.generic_visit(node)

            if self.ds is not None:
                raise Exception("AST Query has more than one EventDataset in it!")
            self.ds = node
            return node

    ds_f = ds_finder()
    ds_f.visit(a)

    if ds_f.ds is None:
        raise Exception(f"AST Query has no root EventDataset: {ast.dump(a)}")

    return ds_f.ds
