import ast
import copy
import inspect
from typing import Any, Dict, Tuple, TypeVar, Union

from .object_stream import ObjectStream

T = TypeVar('T')
S = TypeVar('S')


def remap_by_types(o_stream: ObjectStream[T], var_name: str, var_type: Any, a: ast.AST) \
        -> Tuple[ObjectStream[T], ast.AST]:

    class type_transformer(ast.NodeTransformer):
        def __init__(self, o_stream: ObjectStream[T]):
            self._stream = o_stream
            self._found_types: Dict[Union[str, object], type] = {
                var_name: var_type
            }

        @property
        def stream(self) -> ObjectStream[T]:
            return self._stream

        def process_method_call(self, node: ast.Call, obj_type: type) -> ast.AST:

            # Make reference copies that we'll populate as we go
            r_node = node

            # Deal with default arguments and the method signature
            assert isinstance(r_node.func, ast.Attribute)
            call_method = getattr(obj_type, r_node.func.attr, None)
            if call_method is None:
                return r_node

            sig = inspect.signature(call_method)
            i_arg = 0
            arg_array = list(r_node.args)
            for param in sig.parameters.values():
                if param.name != 'self':
                    if len(arg_array) <= i_arg:
                        if param.default is param.empty:
                            raise ValueError(f'Argument {param.name} on method {r_node.func.attr} '
                                             f'on class {obj_type.__name__} is required.')
                        a = ast.Constant(param.default)
                        arg_array.append(a)
            if len(arg_array) != len(r_node.args):
                r_node = copy.copy(r_node)
                r_node.args = arg_array

            # See if someone wants to process the call
            attr = getattr(obj_type, '_func_adl_type_info')
            if attr is not None:
                r_stream, r_node = attr(self.stream, r_node)
                assert isinstance(r_node, ast.AST)
                self._stream = r_stream

            # And if we have a return annotation, then we should record it!
            self._found_types[r_node] = sig.return_annotation

            return r_node

        def visit_Call(self, node: ast.Call) -> ast.AST:
            t_node = self.generic_visit(node)
            assert isinstance(t_node, ast.Call)
            if isinstance(t_node.func, ast.Attribute):
                # Do we know the type of the value?
                found_type = self._found_types.get(t_node.func.value, None)
                if found_type is not None:
                    t_node = self.process_method_call(t_node, found_type)
            return t_node

        def visit_Name(self, node: ast.Name) -> ast.Name:
            if node.id in self._found_types:
                self._found_types[node] = self._found_types[node.id]
            return node

    tt = type_transformer(o_stream)
    r_a = tt.visit(a)

    return tt.stream, r_a
