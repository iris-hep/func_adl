from abc import ABC, abstractmethod
import ast
from typing import Any, Optional

from .object_stream import ObjectStream, executor_attr_name
from .util_ast import function_call


class EventDataset(ObjectStream, ABC):
    r'''
    A source of event objects (a ROOT file, or a xAOD file). This class
    should be sub-classed with the information about the actual dataset, and
    should never be created on its own.
    '''
    def __init__(self):
        '''
        Should not be called directly. Make sure to initialize this ctor
        or tracking information will be lost.
        '''

        # Create the base AST node.
        ed_ast = function_call('EventDataset', [])

        # Safely store a reference to our executor in the AST in an attribute not used by the
        # the native Python ast module.
        setattr(ed_ast, executor_attr_name, self.execute_result_async)

        # Safely store a reference to this object
        setattr(ed_ast, '_eds_object', self)

        # Let ObjectStream take care of passing around this AST.
        super().__init__(ed_ast)

    def __repr__(self):
        return f"'{self.__class__.__name__}'"

    def __str__(self):
        return self.__class__.__name__

    @abstractmethod
    async def execute_result_async(self, a: ast.AST, title: Optional[str] = None) -> Any:
        '''
        Override in your sub-class. The infrastructure will call this to render the result
        "locally", or as requested by the AST.
        '''
        pass  # pragma: no cover


def find_EventDataset(a: ast.AST) -> ast.Call:
    r'''
    Given an input query ast, find the EventDataset `ast` and return it.

    Args:
        a:      An AST that represents a query

    Returns:
        The `EventDataset` `ast` at the root of this query. It will not be None.

    Exceptions:
        If there is more than one `EventDataset` found in the query or if there
        is no `EventDataset` at the root of the query, then an exception is thrown.
    '''

    class ds_finder(ast.NodeVisitor):
        def __init__(self):
            self.ds: Optional[ast.Call] = None

        def visit_Call(self, node: ast.Call):
            if not isinstance(node.func, ast.Name):
                return self.generic_visit(node)
            if node.func.id != 'EventDataset':
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
