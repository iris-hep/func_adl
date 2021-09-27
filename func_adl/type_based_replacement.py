import ast
import copy
import inspect
from typing import Any, Callable, Dict, Generic, List, NamedTuple, Optional, Tuple, Type, TypeVar, Union

from .object_stream import ObjectStream


U = TypeVar('U')
_FuncAdlFunction = NamedTuple('_FuncAdlFunction', [
    ('name', str),
    ('function', Callable),
    ('processor_function', Optional[Callable[[ObjectStream[U], ast.Call],
                                             Tuple[ObjectStream[U], ast.AST]]])
    ])
_global_functions: Dict[str, _FuncAdlFunction] = {}


def reset_global_functions():
    '''Resets all the global functions we know about.

    Generally only used between tests.
    '''
    global _global_functions
    _global_functions = {}


V = TypeVar('V')


def register_func_adl_function(
    function: Callable,
    processor_function: Optional[Callable[[ObjectStream[V], ast.Call],
                                          Tuple[ObjectStream[V], ast.AST]]]
        ) -> None:
    '''Register a new function for use inside a func_adl expression

    Args:
        function (Callable): The type definition for the function (type st)
        processor_function (Callable[[ObjectStream[T], ast.Call],
            Tuple[ObjectStream[T], ast.AST]]):
            The processor function that can modify the stream, etc.
    '''
    info = _FuncAdlFunction(function.__name__, function, processor_function)
    _global_functions[info.name] = info


W = TypeVar('W')


def func_adl_callable(processor: Optional[Callable[[ObjectStream[W], ast.Call],
                                                   Tuple[ObjectStream[W], ast.AST]]] = None):
    def decorate(function: Callable):
        register_func_adl_function(function, processor)
        return function

    return decorate


def _find_keyword(keywords: List[ast.keyword], name: str) \
        -> Tuple[Optional[ast.AST], List[ast.keyword]]:
    for kw in keywords:
        if kw.arg == name:
            new_kw = list(keywords)
            new_kw.remove(kw)
            return kw.value, new_kw
    return None, keywords


def _fill_in_default_arguments(func: Callable, call: ast.Call) -> Tuple[ast.Call, Type]:
    sig = inspect.signature(func)
    i_arg = 0
    arg_array = list(call.args)
    keywords = list(call.keywords)
    for param in sig.parameters.values():
        if param.name != 'self':
            if len(arg_array) <= i_arg:
                # See if they specified it as a keyword
                a, keywords = _find_keyword(keywords, param.name)
                if a is not None:
                    arg_array.append(a)  # type: ignore
                elif param.default is not param.empty:
                    a = ast.Constant(param.default)
                    arg_array.append(a)
                else:
                    raise ValueError(f'Argument {param.name} is required')

    if len(arg_array) != len(call.args):
        call = copy.copy(call)
        call.args = arg_array
        call.keywords = keywords

    return call, sig.return_annotation


T = TypeVar('T')


def remap_by_types(o_stream: ObjectStream[T], var_name: str, var_type: Any, a: ast.AST) \
        -> Tuple[ObjectStream[T], ast.AST]:

    S = TypeVar('S')

    class type_transformer(ast.NodeTransformer, Generic[S]):
        def __init__(self, o_stream: ObjectStream[S]):
            self._stream = o_stream
            self._found_types: Dict[Union[str, object], type] = {
                var_name: var_type
            }

        @property
        def stream(self) -> ObjectStream[S]:
            return self._stream  # type: ignore

        def process_method_call(self, node: ast.Call, obj_type: type) -> ast.AST:
            # Make reference copies that we'll populate as we go
            r_node = node

            # Deal with default arguments and the method signature
            try:
                assert isinstance(r_node.func, ast.Attribute)
                call_method = getattr(obj_type, r_node.func.attr, None)
                if call_method is None:
                    return r_node

                r_node, return_annotation = _fill_in_default_arguments(call_method, r_node)

                # See if someone wants to process the call
                attr = getattr(obj_type, '_func_adl_type_info')
                if attr is not None:
                    r_stream, r_node = attr(self.stream, r_node)
                    assert isinstance(r_node, ast.AST)
                    self._stream = r_stream

                # And if we have a return annotation, then we should record it!
                self._found_types[r_node] = return_annotation

                return r_node
            except Exception as e:
                f_name = node.func.attr  # type: ignore
                raise ValueError(f'Error processing method call {f_name} on '
                                 f'class {obj_type.__name__} ({str(e)}).') from e

        def process_function_call(self, node: ast.Call, func_info: _FuncAdlFunction) -> ast.AST:
            # Make reference copies that we'll populate as we go
            r_node = node

            try:
                # Deal with default arguments and the method signature
                r_node, return_annotation = _fill_in_default_arguments(func_info.function, r_node)

                # See if someone wants to process the call
                if func_info.processor_function is not None:
                    r_stream, r_node = func_info.processor_function(self.stream, r_node)
                    assert isinstance(r_node, ast.AST)
                    self._stream = r_stream

                # And if we have a return annotation, then we should record it!
                # We do it this late because we might be changing the `r_node`
                # value above!
                self._found_types[r_node] = return_annotation

                return r_node
            except Exception as e:
                raise ValueError(f'Error processing function call {node} on '
                                 f'function {func_info.function.__name__} ({str(e)})') from e

        def visit_Call(self, node: ast.Call) -> ast.AST:
            t_node = self.generic_visit(node)
            assert isinstance(t_node, ast.Call)
            if isinstance(t_node.func, ast.Attribute):
                # Do we know the type of the value?
                found_type = self._found_types.get(t_node.func.value, None)
                if found_type is not None:
                    t_node = self.process_method_call(t_node, found_type)
            elif isinstance(t_node.func, ast.Name):
                if t_node.func.id in _global_functions:
                    t_node = self.process_function_call(t_node, _global_functions[t_node.func.id])
            return t_node

        def visit_Name(self, node: ast.Name) -> ast.Name:
            if node.id in self._found_types:
                self._found_types[node] = self._found_types[node.id]
            return node

    tt = type_transformer(o_stream)
    r_a = tt.visit(a)

    return tt.stream, r_a
