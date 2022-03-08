import ast
from typing import Any, Dict, List, Optional, Tuple

from func_adl.ast.func_adl_ast_utils import FuncADLNodeTransformer
from func_adl.object_stream import ObjectStream


class _extract_metadata(FuncADLNodeTransformer):
    """Extract all the metadata from an expression, and remove the
    metadata nodes. Assume the metadata can all be bubbled to the top and
    has equal precedence.
    """

    def __init__(self):
        super().__init__()
        self._metadata = []

    @property
    def metadata(self) -> List[Dict[str, str]]:
        """Returns the metadata found while scanning expressions
        in the order it was encountered.

        Returns:
            List[Dict[str, str]]: List of all metadata found.
        """
        return self._metadata

    def visit_Call(self, node: ast.Call):
        """Detect a MetaData call, and remove it, storing the
        information.

        Args:
            node (ast.Call): The call node to process.

        Returns:
            ast.AST: The ast without the call node (if need be).
        """
        if isinstance(node.func, ast.Name) and node.func.id == "MetaData":
            self._metadata.append(ast.literal_eval(node.args[1]))
            return self.visit(node.args[0])
        return super().visit_Call(node)


def extract_metadata(a: ast.AST) -> Tuple[ast.AST, List[Dict[str, str]]]:
    """Returns the expresion with extracted metadata and the metadata, in order
    from the outter most to the inner most `MetaData` expressions.

    Args:
        a (ast.AST): The AST potentially containing metadata definitions

    Returns:
        Tuple[ast.AST, List[Dict[str, str]]]: a new AST without the metadata references
        and a list of metadata found.
    """
    e = _extract_metadata()
    a_new = e.visit(a)
    return a_new, e.metadata


def remove_empty_metadata(a: ast.AST) -> ast.AST:
    """Returns a new ast with any empty `MetaData` clauses removed.
    The old ast is not modified.

    Args:
        a (ast.AST): The AST of the query to clean up.

    Returns:
        ast.AST: The cleaned up AST.
    """

    class _cleaner(ast.NodeTransformer):
        def visit_Call(self, node: ast.Call):
            n = self.generic_visit(node)
            assert isinstance(n, ast.Call)
            if isinstance(n.func, ast.Name) and n.func.id == "MetaData":
                if len(n.args) == 2:
                    d = ast.literal_eval(n.args[1])
                    if isinstance(d, dict) and len(d) == 0:
                        return n.args[0]
            return n

    return _cleaner().visit(a)


def lookup_query_metadata(q: ObjectStream, metadata_name: str) -> Optional[Any]:
    """Walk back up the query tree to find metadata_name. Return `None` if not found.

    Args:
        q (ObjectStream): Object stream to walk back up.
        metadata_name (str): Name of the metadata item we are looking for

    Returns:
        Optional[Any]: Either the metadata value or `None`.
    """

    class _finder(ast.NodeVisitor):
        def __init__(self):
            self.ds: Optional[ast.Call] = None
            self._found = None

        @property
        def found(self) -> Optional[Any]:
            return self._found

        def generic_visit(self, node: ast.AST):
            q_metadata = getattr(node, "_q_metadata", None)
            found = False
            if q_metadata is not None:
                if metadata_name in q_metadata:
                    found = True
                    self._found = q_metadata[metadata_name]

            if not found:
                super().generic_visit(node)

    ds_f = _finder()
    ds_f.visit(q.query_ast)

    return ds_f.found
