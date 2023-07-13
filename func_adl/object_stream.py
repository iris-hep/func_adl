from __future__ import annotations

import ast
import copy
import logging
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from make_it_sync import make_sync

from func_adl.util_types import unwrap_iterable

from .util_ast import as_ast, function_call, parse_as_ast

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

    def __init__(self, the_ast: ast.AST, item_type: Type = Any):
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
    def query_ast(self) -> ast.AST:
        """Return the query `ast` that this `ObjectStream` represents

        Returns:
            ast.AST: The python `ast` that is represented by this query
        """
        return self._q_ast

    def clone_with_new_ast(
        self, new_ast: ast.AST, new_type: type[S]
    ) -> ObjectStream[S]:
        clone = copy.deepcopy(self)
        clone._q_ast = new_ast
        clone._item_type = new_type
        return clone  # type: ignore

    def SelectMany(
        self, func: Union[str, ast.Lambda, Callable[[T], Iterable[S]]]
    ) -> ObjectStream[S]:
        r"""
        Given the current stream's object type is an array or other iterable, return
        the items in this objects type, one-by-one. This has the effect of flattening a
        nested array.

        Arguments:

            func:   The function that should be applied to this stream's objects to return
                    an iterable. Each item of the iterable is now the stream of objects.

        Returns:
            A new ObjectStream of the type of the elements.

        Notes:
            - The function can be a `lambda`, the name of a one-line function, a string that
              contains a lambda definition, or a python `ast` of type `ast.Lambda`.
        """
        from func_adl.type_based_replacement import remap_from_lambda

        n_stream, n_ast, rtn_type = remap_from_lambda(
            self, _local_simplification(parse_as_ast(func, "SelectMany"))
        )

        return self.clone_with_new_ast(
            function_call("SelectMany", [n_stream.query_ast, cast(ast.AST, n_ast)]),
            unwrap_iterable(rtn_type),
        )

    def Select(self, f: Union[str, ast.Lambda, Callable[[T], S]]) -> ObjectStream[S]:
        r"""
        Apply a transformation function to each object in the stream, yielding a new type of
        object. There is a one-to-one correspondence between the input objects and output objects.

        Arguments:

            f:      selection function (lambda)

        Returns:

            A new ObjectStream of the transformed elements.

        Notes:
            - The function can be a `lambda`, the name of a one-line function, a string that
              contains a lambda definition, or a python `ast` of type `ast.Lambda`.
        """
        from func_adl.type_based_replacement import remap_from_lambda

        n_stream, n_ast, rtn_type = remap_from_lambda(
            self, _local_simplification(parse_as_ast(f, "Select"))
        )
        return self.clone_with_new_ast(
            function_call("Select", [n_stream.query_ast, cast(ast.AST, n_ast)]),
            rtn_type,
        )

    def Where(
        self, filter: Union[str, ast.Lambda, Callable[[T], bool]]
    ) -> ObjectStream[T]:
        r"""
        Filter the object stream, allowing only items for which `filter` evaluates as true through.

        Arguments:

            filter      A filter lambda that returns True/False.

        Returns:

            A new ObjectStream that contains only elements that pass the filter function

        Notes:
            - The function can be a `lambda`, the name of a one-line function, a string that
              contains a lambda definition, or a python `ast` of type `ast.Lambda`.
        """
        from func_adl.type_based_replacement import remap_from_lambda

        n_stream, n_ast, rtn_type = remap_from_lambda(
            self, _local_simplification(parse_as_ast(filter, "Where"))
        )
        if rtn_type != bool:
            raise ValueError(f"The Where filter must return a boolean (not {rtn_type})")
        return self.clone_with_new_ast(
            function_call("Where", [n_stream.query_ast, cast(ast.AST, n_ast)]),
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

    def AsPandasDF(
        self, columns: Union[str, List[str]] = []
    ) -> ObjectStream[ReturnedDataPlaceHolder]:
        r"""
        Return a pandas stream that contains one item, an pandas `DataFrame`.
        This `DataFrame` will contain all the data fed to it. Only non-array datatypes are
        permitted: the data must look like an Excel table.

        Arguments:

            columns     Array of names of the columns. Will default to "col0", "call1", etc.
                        Exception will be thrown if the number of columns do not match.

        """
        # To get Pandas use the ResultPandasDF function call.
        if isinstance(columns, str):
            columns = [columns]

        return ObjectStream[ReturnedDataPlaceHolder](
            function_call("ResultPandasDF", [self._q_ast, as_ast(columns)])
        )

    as_pandas = AsPandasDF

    def AsROOTTTree(
        self, filename: str, treename: str, columns: Union[str, List[str]] = []
    ) -> ObjectStream[ReturnedDataPlaceHolder]:
        r"""
        Return the sequence of items as a ROOT TTree. Each item in the ObjectStream
        will get one entry in the file. The items must be of types that the infrastructure
        can work with:

            Float               A tree with a single float in each entry will be written.
            vector<float>       A tree with a list of floats in each entry will be written.
            (<tuple>)           A tree with multiple items (leaves) will be written. Each leaf
                                must have one of the above types. Nested tuples are not supported.

        Arguments:

            filename        Name of the file in which a TTree of the objects will be written.
            treename        Name of the tree to be written to the file
            columns         Array of names of the columns. This must match the number of items
                            in a tuple to be written out.

        Returns:

            A new ObjectStream with type [(filename, treename)]. This is because multiple tree's
            may be written by the back end, and need to be concatenated together to get the full
            dataset.  The order of the files back is consistent for different queries on the same
            dataset.
        """
        if isinstance(columns, str):
            columns = [columns]

        return ObjectStream[ReturnedDataPlaceHolder](
            function_call(
                "ResultTTree",
                [self._q_ast, as_ast(columns), as_ast(treename), as_ast(filename)],
            )
        )

    as_ROOT_tree = AsROOTTTree

    def AsParquetFiles(
        self, filename: str, columns: Union[str, List[str]] = []
    ) -> ObjectStream[ReturnedDataPlaceHolder]:
        """Returns the sequence of items as a `parquet` file. Each item in the ObjectStream
        gets a separate entry in the file. The times must be of types that the infrastructure
        can work with:

            Float               A tree with a single float in each entry will be written.
            vector<float>       A tree with a list of floats in each entry will be written.
            (<tuple>)           A tree with multiple items (leaves) will be written. Each leaf
                                must have one of the above types. Nested tuples are not supported.
            {k:v, }             A dictionary with named columns. v is either a float or a vector
                                of floats.

        Arguments:

            filename            Name of a file in which the data will be written. Depending on
                                where the data comes from this may not be used - consider it a
                                suggestion.
            columns             If the data does not arrive by dictionary, then these are the
                                column names.

        Returns:

            A new `ObjectStream` with type `[filename]`. This is because multiple files may be
            written by the backend - the data should be concatenated together to get a final
            result. The order of the files back is consistent for different queries on the same
            dataset.
        """
        if isinstance(columns, str):
            columns = [columns]

        return ObjectStream[ReturnedDataPlaceHolder](
            function_call(
                "ResultParquet", [self._q_ast, as_ast(columns), as_ast(filename)]
            )
        )

    as_parquet = AsParquetFiles

    def AsAwkwardArray(
        self, columns: Union[str, List[str]] = []
    ) -> ObjectStream[ReturnedDataPlaceHolder]:
        r"""
        Return a pandas stream that contains one item, an `awkward` array, or dictionary of
        `awkward` arrays. This `awkward` will contain all the data fed to it.

        Arguments:

            columns     Array of names of the columns. Will default to "col0", "call1", etc.
                        Exception will be thrown if the number of columns do not match.

        Returns:

            An `ObjectStream` with the `awkward` array data as its one and only element.
        """
        if isinstance(columns, str):
            columns = [columns]

        return ObjectStream[ReturnedDataPlaceHolder](
            function_call("ResultAwkwardArray", [self._q_ast, as_ast(columns)])
        )

    as_awkward = AsAwkwardArray

    def _get_executor(
        self,
        executor: Optional[Callable[[ast.AST, Optional[str]], Awaitable[Any]]] = None,
    ) -> Callable[[ast.AST, Optional[str]], Awaitable[Any]]:
        r"""
        Returns an executor that can be used to run this.
        Logic separated out as it is used from several different places.

        Arguments:
            executor            Callback to run the AST. Can be synchronous or coroutine.

        Returns:
            An executor that is either synchronous or a coroutine.
        """
        if executor is not None:
            return executor

        # Dig into the AST until we find a node with an executor reference attached. The AST is
        # traversed by looking recursively into the source of each ObjectStream, which is always
        # the first argument in the ast.Call node.
        node = self._q_ast
        while not hasattr(node, executor_attr_name):
            node = node.args[0]  # type: ignore

        # Extract the executor from this reference.
        return getattr(node, executor_attr_name)

    async def value_async(
        self,
        executor: Optional[Callable[[ast.AST, Optional[str]], Any]] = None,
        title: Optional[str] = None,
    ) -> Any:
        r"""
        Evaluate the ObjectStream computation graph. Tracks back to the source dataset to
        understand how to evaluate the AST. It is possible to pass in an executor to override that
        behavior (used mostly for testing).

        Arguments:

            executor        A function that when called with the ast will return a future for the
                            result. If None, then uses the default executor. Normally is none
                            and the default executor specified by the `EventDatasource` is called
                            instead.
            title           Optional title to hand to the transform

        Returns

            The first element of the ObjectStream after evaluation.


        Note

            This is the non-blocking version - it will return a future which can
            be `await`ed upon until the query is done.
        """
        # Fetch the executor
        exe = self._get_executor(executor)

        # Run it
        from func_adl.ast.meta_data import remove_empty_metadata

        return await exe(remove_empty_metadata(self._q_ast), title)

    value = make_sync(value_async)
