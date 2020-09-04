import ast
from func_adl.util_ast import function_call
from typing import Tuple, List, Optional, cast, Any


def is_call_of(node: ast.AST, func_name: str) -> bool:
    '''
    Return true if this AST node is a function call
    '''
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Name):
        return False

    return node.func.id == func_name


def unpack_Call(node: ast.Call) -> Tuple[Optional[str], Optional[List[ast.AST]]]:
    '''
    Unpack the contents of a call ast.

    Args:
        node        An ast.Call node to unpack

    Returns:
        name        Name fo the function to call. None if it isn't a function call.
        args        List of arguments, None if this isn't a function call.
    '''
    assert isinstance(node, ast.Call)
    if not isinstance(node.func, ast.Name):
        return (None, None)

    args = cast(List[ast.AST], node.args)  # type: List[ast.AST]
    return (node.func.id, args)


class FuncADLNodeTransformer (ast.NodeTransformer):
    ''' Utility class to help with transforming ast's that
    we typically have to deal with in func_adl. In particular:

        - a ast.Call func_name is turned into a call_func_name(self, node, args)
    '''

    def visit_Call(self, node: ast.Call):
        ''' Parse the Call node, split out a function
        and its arguments if such a call exists.
        '''
        func_name, args = unpack_Call(node)
        if func_name is None:
            return self.generic_visit(node)

        visitor = getattr(self, f'call_{func_name}', None)
        if visitor is None:
            return self.generic_visit(node)
        else:
            return visitor(node, args)


class FuncADLNodeVisitor (ast.NodeVisitor):
    ''' Utility class to help with transforming ast's that
    we typically have to deal with in func_adl. In particular:

        - a ast.Call func_name is turned into a call_func_name(self, node, args)
        - If you take over a call, you have to process all dependent ast's it. If you don't,
          then generic_visit is used to process the calls.
    '''

    def visit_Call(self, node: ast.Call) -> Any:
        ''' Parse the Call node, split out a function
        and its arguments if such a call exists.
        '''
        func_name, args = unpack_Call(node)
        if func_name is None:
            return self.generic_visit(node)

        visitor = getattr(self, f'call_{func_name}', None)
        if visitor is not None:
            return visitor(node, args)
        else:
            return self.generic_visit(node)


# Default list of functions that we allow in here when altering extension function changes.
# TODO: #50 Get rid of this now that qastle supports this stuff
default_list_of_functions = [
    'Select', 'SelectMany', 'Where',
    'First',
    'ResultTTree', 'ResultAwkwardArray', 'ResultPandasDF',
    'Min', 'Max', 'Sum', 'Aggregate', 'Count',
]


def change_extension_functions_to_calls(a: ast.AST,
                                        function_names: List[str] = default_list_of_functions) \
        -> ast.AST:
    '''Given a call tree for a query, find things that look like
    `seq.Select(x: f(x))` and change them to `Select(seq, x: f(x))`.

    Do this for the given list of functions.
    '''
    class transform_calls(ast.NodeTransformer):
        def visit_Call(self, call_node: ast.Call) -> Optional[ast.AST]:
            node = self.generic_visit(call_node)
            if node is None or not isinstance(node, ast.Call):
                return node
            if not isinstance(node.func, ast.Attribute):
                return node
            if node.func.attr not in function_names:
                return node
            return function_call(node.func.attr,
                                 cast(List[ast.AST], [node.func.value] + node.args))
    return transform_calls().visit(a)
