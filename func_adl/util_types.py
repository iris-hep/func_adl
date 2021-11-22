

import ast
from typing import Any, Dict, Optional, Tuple, Type


class _type_follower(ast.NodeVisitor):
    'Follow the types through an expression the best we can'
    def __init__(self, initial_types: Dict[str, Type]):
        super().__init__()
        self._named_types = initial_types
        self._node_types: Dict[ast.AST, Type] = {}

    def lookup_node_type(self, node: ast.AST) -> Optional[Type]:
        if node in self._node_types:
            return self._node_types[node]
        return None

    def visit_Lambda(self, node: ast.Lambda):
        super().generic_visit(node)
        self._node_types[node] = self.lookup_node_type(node.body)

    def visit_Name(self, node: ast.Name):
        super().generic_visit(node)
        if node.id in self._named_types:
            self._node_types[node] = self._named_types[node.id]
        else:
            self._node_types[node] = Any

    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, str):
            self._node_types[node] = str
        elif isinstance(node.value, bool):
            self._node_types[node] = bool
        elif isinstance(node.value, int):
            self._node_types[node] = int
        elif isinstance(node.value, float):
            self._node_types[node] = float


def follow_types(call: ast.Lambda, args: Tuple[Type, ...]) -> Type:
    """
    Follow the types of the arguments of a lambda function, given the
    incoming types. `Any` is used if we do not know what is coming back.
    """
    assert len(args) == len(call.args.args)
    arg_types = zip([arg.arg for arg in call.args.args], args)
    v = _type_follower({a[0]: a[1] for a in arg_types})
    v.visit(call)
    return v.lookup_node_type(call)
