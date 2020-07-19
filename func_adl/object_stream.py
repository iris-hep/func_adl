# An Object stream represents a stream of objects, floats, integers, etc.
import ast
from typing import Any, Callable, Union, cast, Awaitable

from make_it_sync import make_sync

from .util_ast import as_ast, function_call, parse_as_ast


class ObjectStreamException(Exception):
    'Exception thrown by the ObjectStream object.'
    def __init__(self, msg):
        Exception.__init__(self, msg)


class ObjectStream:
    r'''
    Represents the AST to produce a stream of objects. The objects can be events,
    jets, electrons, or just floats, or arrays of floats.

    `ObjectStream` holds onto the AST that will produce this stream of objects.
    '''
    def __init__(self, the_ast: ast.AST):
        r"""
        Initialize the stream with the ast that will produce this stream of objects.
        The user will almost never use this initializer.
        """
        self._ast = the_ast

    def SelectMany(self, func: Union[str, ast.Lambda]):
        r"""
        Given the current stream's object type is an array or other iterable, return
        the items in this objects type, one-by-one. This has the effect of flattening a
        nested array.

        Args:
            func:   The function that should be applied to this stream's objects to return
                    an iterable. Each item of the iterable is now the stream of objects.

        Returns:
            A new ObjectStream.
        """
        return ObjectStream(function_call("SelectMany", [self._ast, cast(ast.AST, parse_as_ast(func))]))

    def Select(self, f: Union[str, ast.Lambda]):
        r"""
        Apply a transformation function to each object in the stream, yielding a new type of
        object.

        Args:
            f:      selection function (lambda)

        Returns:
            A new ObjectStream of the transformed elements.
        """
        return ObjectStream(function_call("Select", [self._ast, cast(ast.AST, parse_as_ast(f))]))

    def Where(self, filter):
        r'''
        Filter the object stream, allowing only items for which `filter` evaluates as try through.

        Args:
            filter:     A filter lambda that returns True/False.

        Returns:
            A new ObjectStream that contains only elements that pass the filter function
        '''
        return ObjectStream(function_call("Where", [self._ast, cast(ast.AST, parse_as_ast(filter))]))

    def AsPandasDF(self, columns=[]):
        r"""
        Return a pandas dataframe. We do this by running the conversion.

        columns - Array of names of the columns. Will default to "col0", "call1", etc.
        """

        # To get Pandas use the ResultPandasDF function call.
        return ObjectStream(function_call("ResultPandasDF", [self._ast, as_ast(columns)]))

    def AsROOTTTree(self, filename, treename, columns=[]):
        r"""
        Return the sequence of items as a ROOT TTree. Each item in the ObjectStream
        will get one entry in the file. The items must be of types that the infrastructure
        can work with:
            Float:              A tree with a single float in each entry will be written.
            vector<float>:      A tree with a list of floats in each entry will be written.
            (<tuple>):          A tree with multiple items (leaves) will be written. Each leaf
                                must have one of the above types. Nested tuples are not supported.

        Args:
            filename:       Name of the file in which a TTree of the objects will be written.
            treename:       Name of the tree to be written to the file
            columns:        Array of names of the columns. This must match the number of items
                            in a tuple to be written out.

        Returns:
            A new ObjectStream with type [(filename, treename)]. This is because multiple tree's
            may be written by the back end, and need to be concatenated together to get the full
            dataset.
        """
        return ObjectStream(function_call("ResultTTree", [self._ast, as_ast(columns), as_ast(treename), as_ast(filename)]))

    def AsAwkwardArray(self, columns=[]):
        r'''
        Terminal - take the AST and return a root file.

        columns - Array of names of the columns
        '''
        return ObjectStream(function_call("ResultAwkwardArray", [self._ast, as_ast(columns)]))

    def _get_executor(self, executor: Callable[[ast.AST], Awaitable[Any]] = None) -> Callable[[ast.AST], Awaitable[Any]]:
        r'''
        Returns an executor that can be used to run this.
        Logic seperated out as it is used from several different places.

        Arguments:
            executor            Callback to run the AST. Can be synchronous or coroutine.

        Returns:
            An executor that is either synchronous or a coroutine.
        '''
        if executor is not None:
            return executor

        from .event_dataset import find_ed_in_ast
        ed = find_ed_in_ast(self._ast)

        return ed.execute_result_async

    async def value_async(self, executor: Callable[[ast.AST], Any] = None) -> Any:
        r'''
        Evaluate the AST. Tracks back to the source dataset to understand how
        to evaluate the AST. It is possible to pass in an executor to override that
        behavior (used mostly for testing).

        Args:
            executor:       A function that when called with the ast will return a future for the
                            result. If None, then uses the default executor.

        '''
        # Fetch the executor
        exe = self._get_executor(executor)

        # Run it
        return await exe(self._ast)

    value = make_sync(value_async)
