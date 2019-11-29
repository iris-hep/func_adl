import ast


def is_call_of(node: ast.AST, func_name: str) -> bool:
    '''
    Return true if this AST node is a function call
    '''
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Name):
        return False

    return node.func.id == func_name


class FuncADLNodeTransformer (ast.NodeTransformer):
    ''' Utility class to help with transforming ast's that
    we typically have to deal with in func_adl. In particular:

        - a ast.Call func_name is turned into a call_func_name(self, node, args)
    '''

    def visit_Call(self, node):
        ''' Parse the Call node, split out a function
        and its arguments if such a call exists.
        '''
        assert isinstance(node, ast.Call)
        if not isinstance(node.func, ast.Name):
            return node

        func_name = node.func.id
        visitor = getattr(self, f'call_{func_name}', None)
        return node if visitor is None else visitor(node, node.args)
