from abc import ABC
from typing import Any, Type, TypeVar

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
