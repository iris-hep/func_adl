from __future__ import annotations

import ast
import copy
import logging
from typing import Any, Callable, Dict, Generic, Iterable, Type, TypeVar, Union

from func_adl.util_types import unwrap_iterable

from .util_ast import as_ast, check_ast, function_call, parse_as_ast

# Attribute that will be used to store the executor reference
executor_attr_name = "_func_adl_executor"

T = TypeVar("T")
S = TypeVar("S")


class ReturnedDataPlaceHolder:
    """Type returned for awkward, etc.,"""

    pass


def _local_simplification(a: ast.Lambda) -> ast.Lambda:
    """Simplify the AST by removing unnecessary statements and
    syntatic sugar
    """
    from func_adl.ast.syntatic_sugar import resolve_syntatic_sugar

    r = resolve_syntatic_sugar(a)
    assert isinstance(r, ast.Lambda), "resolve_syntatic_sugar must return a lambda"
    return r


class ObjectStream(Generic[T]):
    r"""
    The objects can be events, jets, electrons, or just floats, or arrays of floats.

    `ObjectStream` holds onto the AST that will produce this stream of objects. The chain
    of `ObjectStream` objects, linked together, is a DAG that stores the user's intent.

    Every stream has an _object type_. This is the type of the elements of the stream. For example,
    the top stream, the objects are of type `Event` (or `xADOEvent`). If you transform an `Event`
    into a list of jets, then the object type will be a list of `Jet` objects. Each element of the
    stream is an array. You can also lift this second array of `Jets` and turn it into a plain
    stream of `Jets` using the `SelectMany` method below. In that case, you'll no longer be able
    to tell the boundary between events.

    `TypeVar` T is the item type (so this represents, if one were to think of this as loop-a-ble,
    `Iterable[T]`).
    """

    def __init__(self, the_ast: ast.expr, item_type: Type = Any):  # type: ignore
        r"""
        Initialize the stream with the ast that will produce this stream of objects.
        The user will almost never use this initializer.
        """
        self._q_ast = the_ast
        self._item_type = item_type

    @property
    def item_type(self) -> Type:
        "Returns the type of the item this is a stream of. None if not known."
        return self._item_type

    @property
    def query_ast(self) -> ast.expr:
        """Return the query `ast` that this `ObjectStream` represents

        Returns:
            ast.AST: The python `ast` that is represented by this query
        """
        return self._q_ast

    def clean_ast(self) -> ast.AST:
        """Return a cleaned copy of the query AST before execution."""
        from func_adl.ast.meta_data import (
            remove_duplicate_metadata,
            remove_empty_metadata,
        )

        # Keep metadata cleanup in one place so all execution paths are consistent.
        return remove_duplicate_metadata(remove_empty_metadata(self._q_ast))

    def clone_with_new_ast(self, new_ast: ast.AST, new_type: type[S]) -> ObjectStream[S]:
        clone = copy.copy(self)
        clone._q_ast = new_ast
        clone._item_type = new_type
        return clone  # type: ignore

    def SelectMany(
        self,
        func: Union[str, ast.Lambda, Callable[[T], Iterable[S]]],
        known_types: Dict[str, Any] = {},
    ) -> ObjectStream[S]:
        r"""
        Given the current stream's object type is an array or other iterable, return
        the items in this objects type, one-by-one. This has the effect of flattening a
        nested array.

        Arguments:

            func:   The function that should be applied to this stream's objects to return
                    an iterable. Each item of the iterable is now the stream of objects.
            known_types: Internal use only - for passing captured variables from above in.

        Returns:
            A new ObjectStream of the type of the elements.

        Notes:
            - The function can be a `lambda`, the name of a one-line function, a string that
              contains a lambda definition, or a python `ast` of type `ast.Lambda`.
        """
        from func_adl.type_based_replacement import remap_from_lambda

        n_stream, n_ast, rtn_type = remap_from_lambda(
            self, _local_simplification(parse_as_ast(func, "SelectMany")), known_types
        )
        check_ast(n_ast)

        return self.clone_with_new_ast(
            function_call("SelectMany", [n_stream.query_ast, n_ast]),
            unwrap_iterable(rtn_type),
        )

    def Select(
        self, f: Union[str, ast.Lambda, Callable[[T], S]], known_types: Dict[str, Any] = {}
    ) -> ObjectStream[S]:
        r"""
        Apply a transformation function to each object in the stream, yielding a new type of
        object. There is a one-to-one correspondence between the input objects and output objects.

        Arguments:

            f:      selection function (lambda)
            known_types: Internal use only - for passing captured variables from above in.

        Returns:

            A new ObjectStream of the transformed elements.

        Notes:
            - The function can be a `lambda`, the name of a one-line function, a string that
              contains a lambda definition, or a python `ast` of type `ast.Lambda`.
        """
        from func_adl.type_based_replacement import remap_from_lambda

        n_stream, n_ast, rtn_type = remap_from_lambda(
            self, _local_simplification(parse_as_ast(f, "Select")), known_types
        )
        check_ast(n_ast)
        return self.clone_with_new_ast(
            function_call("Select", [n_stream.query_ast, n_ast]),
            rtn_type,
        )

    def Where(
        self, filter: Union[str, ast.Lambda, Callable[[T], bool]], known_types: Dict[str, Any] = {}
    ) -> ObjectStream[T]:
        r"""
        Filter the object stream, allowing only items for which `filter` evaluates as true through.

        Arguments:

            filter      A filter lambda that returns True/False.
            known_types: Internal use only - for passing captured variables from above in.

        Returns:

            A new ObjectStream that contains only elements that pass the filter function

        Notes:
            - The function can be a `lambda`, the name of a one-line function, a string that
              contains a lambda definition, or a python `ast` of type `ast.Lambda`.
        """
        from func_adl.type_based_replacement import remap_from_lambda

        n_stream, n_ast, rtn_type = remap_from_lambda(
            self, _local_simplification(parse_as_ast(filter, "Where")), known_types
        )
        check_ast(n_ast)
        if rtn_type != bool:
            raise ValueError(
                f"The Where filter must return a boolean (not {rtn_type}) for expression "
                f"{ast.unparse(n_ast)}"
            )
        return self.clone_with_new_ast(
            function_call("Where", [n_stream.query_ast, n_ast]),
            self.item_type,
        )

    def MetaData(self, metadata: Dict[str, Any]) -> ObjectStream[T]:
        """Add metadata to the current object stream. The metadata is an arbitrary set of string
        key-value pairs. The backend must be able to properly interpret the metadata.

        Returns:
            ObjectStream: A new stream, of the same type and contents, but with metadata added.
        """
        return self.clone_with_new_ast(
            function_call("MetaData", [self._q_ast, as_ast(metadata)]), self.item_type
        )

    def QMetaData(self, metadata: Dict[str, Any]) -> ObjectStream[T]:
        """Add query metadata to the current object stream.

        - Metadata is never transmitted to any back end
        - Metadata is per-query, not per sample.

        Warnings are issued if metadata is overwriting metadata.

        Args:
            metadata (Dict[str, Any]): Metadata to be used later

        Returns:
            ObjectStream[T]: The object stream, with metadata attached
        """
        from .ast.meta_data import lookup_query_metadata

        q_metadata = {}
        for k, v in metadata.items():
            found_md = lookup_query_metadata(self, k)
            add_md = False
            if found_md is None:
                add_md = True
            elif found_md != v:
                logging.getLogger(__name__).info(
                    f'Overwriting metadata "{k}" from its old value of "{found_md}" to "{v}"'
                )
                add_md = True
            if add_md:
                q_metadata[k] = v  # type: ignore

        base_ast = self.query_ast
        if len(q_metadata) > 0:
            new_self = self.clone_with_new_ast(copy.copy(base_ast), self.item_type)
            new_self.query_ast._q_metadata = q_metadata  # type: ignore
            return new_self
        else:
            return self.clone_with_new_ast(base_ast, self.item_type)
