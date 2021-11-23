import ast
from typing import Any, Dict, Optional, Tuple, Type
import logging
import inspect


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

    def visit_UnaryOp(self, node: ast.UnaryOp):
        super().generic_visit(node)
        self._node_types[node] = self.lookup_node_type(node.operand)

    def visit_BinOp(self, node: ast.BinOp):
        super().generic_visit(node)
        t_left = self.lookup_node_type(node.left)
        t_right = self.lookup_node_type(node.right)

        if (t_left == Any) or (t_right == Any):
            self._node_types[node] = Any
        elif (t_left == float) or (t_right == float):
            self._node_types[node] = float
        elif isinstance(node.op, ast.Div):
            self._node_types[node] = float
        else:
            self._node_types[node] = int

    def visit_Name(self, node: ast.Name):
        super().generic_visit(node)
        if node.id in self._named_types:
            self._node_types[node] = self._named_types[node.id]
        else:
            self._node_types[node] = Any
            logging.getLogger(__name__).warning(f'Unknown type for {node.id}')

    def visit_Constant(self, node: ast.Constant):
        self._node_types[node] = type(node.value)

    def visit_Call(self, node: ast.Call):
        super().generic_visit(node)
        if isinstance(node.func, ast.Attribute):
            # Use type hinting to get the type of the method!
            t = self.lookup_node_type(node.func.value)
            r = Any
            if t is not Any:
                attr = getattr(t, node.func.attr, None)
                if attr is not None:
                    sig = inspect.signature(attr)
                    if sig.return_annotation is not inspect.Signature.empty:
                        r = sig.return_annotation
            self._node_types[node] = r
            if r == Any:
                logging.getLogger(__name__) \
                    .warning(f'Unknown type for method {ast.dump(node.func)}')
        else:
            self._node_types[node] = Any
            logging.getLogger(__name__) \
                .warning(f'Unknown type for method call {ast.dump(node.func)}')


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
