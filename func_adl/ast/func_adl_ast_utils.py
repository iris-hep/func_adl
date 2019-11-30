import ast
from typing import Tuple, List


def is_call_of(node: ast.AST, func_name: str) -> bool:
    '''
    Return true if this AST node is a function call
    '''
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Name):
        return False

    return node.func.id == func_name

def unpack_Call(node: ast.Call) -> Tuple[str, List[ast.AST]]:
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

    return (node.func.id, node.args)


class FuncADLNodeTransformer (ast.NodeTransformer):
    ''' Utility class to help with transforming ast's that
    we typically have to deal with in func_adl. In particular:

        - a ast.Call func_name is turned into a call_func_name(self, node, args)
    '''

    def visit_Call(self, node: ast.Call):
        ''' Parse the Call node, split out a function
        and its arguments if such a call exists.
        '''
        # First, visit one down.
        visited_node = ast.NodeTransformer.generic_visit(self, node)
        assert isinstance(visited_node, ast.Call)

        func_name, args = unpack_Call(visited_node)
        if func_name is None:
            return visited_node

        visitor = getattr(self, f'call_{func_name}', None)
        return node if visitor is None else visitor(visited_node, args)
