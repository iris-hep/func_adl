# An Object stream represents a stream of objects, floats, integers, etc.
from func_adl import Select, Where, SelectMany
from func_adl import ResultTTree, ResultAwkwardArray, ResultPandasDF
from func_adl.util_ast_LINQ import parse_as_ast
# import ast
from typing import Any, Callable
import asyncio
import ast
import os


class ObjectStreamException(BaseException):
    'Exception thrown by the ObjectStream object.'
    def __init__(self, msg):
        BaseException.__init__(self, msg)


class ObjectStream:
    r'''
    Represents the AST to produce a stream of objects. The objects can be events,
    jets, electrons, or just floats, or arrays of floats.

    `ObjectStream` holds onto the AST that will produce this stream of objects.
    '''
    def __init__(self, the_ast):
        r"""
        Initialize the stream with the ast that will produce this stream of objects.
        The user will almost never use this initializer.
        """
        self._ast = the_ast

    def SelectMany(self, func):
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
        return ObjectStream(SelectMany(self._ast, parse_as_ast(func)))

    def Select(self, f):
        r"""
        Apply a transformation function to each object in the stream, yielding a new type of
        object.

        Args:
            f:      selection function (lambda)

        Returns:
            A new ObjectStream of the transformed elements.
        """
        return ObjectStream(Select(self._ast, parse_as_ast(f)))

    def Where(self, filter):
        r'''
        Filter the object stream, allowing only items for which `filter` evaluates as try through.

        Args:
            filter:     A filter lambda that returns True/False.

        Returns:
            A new ObjectStream that contains only elements that pass the filter function
        '''
        return ObjectStream(Where(self._ast, parse_as_ast(filter)))

    def AsPandasDF(self, columns=[]):
        r"""
        Return a pandas dataframe. We do this by running the conversion.

        columns - Array of names of the columns. Will default to "col0", "call1", etc.
        """

        # We do this by first generating a simple ROOT file, then loading it into a dataframe with
        # uproot.
        return ObjectStream(ResultPandasDF(self._ast, columns))

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
        return ObjectStream(ResultTTree(self._ast, columns, treename, filename))

    def AsAwkwardArray(self, columns=[]):
        r'''
        Terminal - take the AST and return a root file.

        columns - Array of names of the columns
        '''
        return ObjectStream(ResultAwkwardArray(self._ast, columns))

    def _get_executor(self, executor: Callable[[ast.AST], Any] = None) -> Callable[[ast.AST], Any]:
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

        raise BaseException('No idea what to do for a default executor')

    async def _exe_as_task(self, executor: Callable[[ast.AST], Any]) -> Any:
        'Run the executor as a task, no matter if it is a co routine or not'
        r = executor(self._ast)

        if asyncio.iscoroutine(r):
            return await r
        else:
            return r

    async def future_value(self, executor: Callable[[ast.AST], Any] = None) -> None:
        r'''
        Start the evaluation of the AST. Returns a promise that can be used to check on the progress.
        Built to allow one to make lots of requests at the same time, and have a back-end server address
        them simultaneously.

        Args:
            executor:       A function that when called with the ast will return a future for the
                            result. If None, then uses the default executor (or throws if none is
                            defined).

        '''
        # Fetch the executor
        exe = self._get_executor(executor)

        # We do not know if this thing is synchronous or not, so we have to wrap it in a task.
        return await self._exe_as_task(exe)

    def value(self, executor: Callable[[ast.AST], Any] = None) -> Any:
        r"""
        Trigger the evaluation of the AST. Returns the results of the execution to the caller.
        WARNING: It is an error to call this if the event loop for async futures is already running.
                 This comes up most surprisingly when running in a Jupyter notebook, which starts an
                 event loop behind your back. So you must use `await` and `future_value`.

        Args:
            executor:       A function that when called with the ast will return the result. If
                            None, then use the default executor.

        Returns:
            Whatever the executor evaluates to.
        """
        # Event loops to run async tasks in python are "funny". We can't wait for a task if
        # one of those loops is running. So that is improper use of the library.
        fail = False
        try:
            loop = asyncio.get_running_loop()
            fail = True
        except BaseException:
            pass
        if fail:
            raise ObjectStreamException('A python async event loop is already running. You must use future_value.')

        # Run our own event loop to make sure we get back the result and we are self contained
        # and don't stomp on anyone. Since we aren't just waiting on sockets, we will have to
        # have an OS difference here.
        if os.name == 'nt':
            loop = asyncio.ProactorEventLoop()   # for subprocess' pipes on Windows
        else:
            loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.future_value(executor))
