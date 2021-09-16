
import ast
from func_adl.ast.func_adl_ast_utils import FuncADLNodeTransformer
from typing import Dict, List, Tuple


class _extract_metadata(FuncADLNodeTransformer):
    '''Extract all the metadata from an expression, and remove the
    metadata nodes. Assume the metadata can all be bubbled to the top and
    has equal precedence.
    '''
    def __init__(self):
        super().__init__()
        self._metadata = []

    @property
    def metadata(self) -> List[Dict[str, str]]:
        '''Returns the metadata found while scanning expressions
        in the order it was encountered.

        Returns:
            List[Dict[str, str]]: List of all metadata found.
        '''
        return self._metadata

    def visit_Call(self, node: ast.Call):
        '''Detect a MetaData call, and remove it, storing the
        information.

        Args:
            node (ast.Call): The call node to process.

        Returns:
            ast.AST: The ast without the call node (if need be).
        '''
        if isinstance(node.func, ast.Name) and node.func.id == 'MetaData':
            self._metadata.append(ast.literal_eval(node.args[1]))
            return self.visit(node.args[0])
        return super().visit_Call(node)
        return super().visit_Call(node)


def extract_metadata(a: ast.AST) -> Tuple[ast.AST, List[Dict[str, str]]]:
    '''Returns the expresion with extracted metadata and the metadata, in order
    from the outter most to the inner most `MetaData` expressions.

    Args:
        a (ast.AST): The AST potentially containing metadata definitions

    Returns:
        Tuple[ast.AST, List[Dict[str, str]]]: a new AST without the metadata references
        and a list of metadata found.
    '''
    e = _extract_metadata()
    a_new = e.visit(a)
    return a_new, e.metadata
