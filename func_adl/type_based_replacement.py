import ast
import copy
import inspect
from typing import (Any, Callable, Dict, Generic, List, NamedTuple, Optional,
                    Tuple, Type, TypeVar, Union)
import sys

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


if sys.version_info >= (3, 8):  # pragma: no cover
    def _as_literal(p: Union[str, int, float, bool, None]) -> ast.Constant:
        return ast.Constant(value=p, kind=None)

    def get_type_args(tp):
        import typing
        return typing.get_args(tp)
else:  # pragma: no cover
    def _as_literal(p: Union[str, int, float, bool, None]):
        if isinstance(p, str):
            return ast.Str(p)
        elif isinstance(p, (int, float)):
            return ast.Num(p)
        elif isinstance(p, bool):
            return ast.NameConstant(p)
        elif p is None:
            return ast.NameConstant(None)
        else:
            raise ValueError(f'Unknown type {type(p)} - do not know how to make a literal!')

    def get_type_args(tp):
        """Get type arguments with all substitutions performed.
        For unions, basic simplifications used by Union constructor are performed.
        Examples::
            get_args(Dict[str, int]) == (str, int)
            get_args(int) == ()
            get_args(Union[int, Union[T, int], str][int]) == (int, str)
            get_args(Union[int, Tuple[T, int]][str]) == (int, Tuple[str, int])
            get_args(Callable[[], T][int]) == ([], int)
        """
        from typing import _AnnotatedAlias, GenericAlias, _GenericAlias, _is_param_expr
        import collections
        import types
        if isinstance(tp, _AnnotatedAlias):
            return (tp.__origin__,) + tp.__metadata__
        if isinstance(tp, (_GenericAlias, GenericAlias)):
            res = tp.__args__
            if (tp.__origin__ is collections.abc.Callable
                    and not (len(res) == 2 and _is_param_expr(res[0]))):
                res = (list(res[:-1]), res[-1])
            return res
        if isinstance(tp, types.UnionType):
            return tp.__args__
        return ()


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
                    a = _as_literal(param.default)
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
                attr = getattr(obj_type, '_func_adl_type_info', None)
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


def remap_from_lambda(o_stream: ObjectStream[T], l_func: ast.Lambda) \
        -> Tuple[ObjectStream[T], ast.AST]:
    orig_class = getattr(o_stream, '__orig_class__', None)
    var_types = None
    if orig_class is not None:
        var_types = get_type_args(orig_class)

    if var_types is None:
        base_classes = getattr(o_stream, '__orig_bases__', None)
        if base_classes is None:
            return o_stream, l_func
        var_types = get_type_args(base_classes[0])

    if len(var_types) == 0:
        return o_stream, l_func

    assert len(l_func.args.args) == 1
    var_name = l_func.args.args[0].arg
    stream, new_body = remap_by_types(o_stream, var_name, var_types[0], l_func.body)
    return stream, ast.Lambda(l_func.args, new_body)
