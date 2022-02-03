from __future__ import annotations

import ast
import copy
import inspect
import logging
import sys
import typing
from dataclasses import dataclass
from typing import (Any, Callable, Dict, Generic, Iterable, List, NamedTuple,
                    Optional, Tuple, Type, TypeVar, Union, get_args,
                    get_origin)

from func_adl.util_ast import scan_for_metadata
from func_adl.util_types import (get_class_name, get_method_and_class,
                                 is_iterable, resolve_type_vars,
                                 unwrap_iterable)

from .object_stream import ObjectStream

# Internal named tuple containing info for a global function
# definitions. Functions with these names can be used inline
# in func_adl expressions, and will trigger the processor and
# also be subject to normal argument resolution.
U = TypeVar('U')
_FuncAdlFunction = NamedTuple('_FuncAdlFunction', [
    ('name', str),
    ('function', Callable),
    ('processor_function', Optional[Callable[[ObjectStream[U], ast.Call],
                                             Tuple[ObjectStream[U], ast.AST]]])
    ])
_global_functions: Dict[str, _FuncAdlFunction] = {}


def _load_default_global_functions():
    'Define the python standard functions that map straight through'
    # TODO: Add in other functions

    def my_abs(x: float) -> float:
        ...

    _global_functions['abs'] = _FuncAdlFunction('abs', my_abs, None)


_load_default_global_functions()


def reset_global_functions():
    '''Resets all the global functions we know about.

    Generally only used between tests.
    '''
    global _global_functions, _g_collection_classes
    _global_functions = {}
    _load_default_global_functions()
    _g_collection_classes = {}
    _load_g_collection_classes()


V = TypeVar('V')


def register_func_adl_function(
    function: Callable,
    processor_function: Optional[Callable[[ObjectStream[V], ast.Call],
                                          Tuple[ObjectStream[V], ast.AST]]]
        ) -> None:
    '''Register a new function for use inside a func_adl expression.

    * A function registered will have its arguments filled in - defaults,
    keywords converted to positional, etc.
    * If a processor function is provided, it will be called as the call
    site si being examined. Any bit can be modified.

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
    '''Dectorator that will declare a function that can be used inline in
    a `func_adl` expression. The body of the function, what the backend
    translates it to, must be given by another route (e.g. via `MetaData`
    and the `processor` argument).

    ```python
    @func_adl_callable
    def my_func(arg1: float, arg2: float = 10) -> float:
        ...
    ```

    This example will declare `my_func`. If it is used like this:
    `Select(lambda x: my_func(arg1=x))`, it will be translated into
    a call sent to the backend that looks like `Select(lambda x: my_func(x, 10))`.

    If `processor` is provided, it will be called as the call site is being
    processed. One can add items to the `ObjectStream` or even modify/check the
    arguments of the call. An example:

    ```python
    def processor(s: ObjectStream[T], a: ast.Call) -> Tuple[ObjectStream[T], ast.Call]:
        new_s = s.MetaData({'j': 'func_stuff'})
        return new_s, a

    @func_adl_callable(MySqrtProcessor)
    def MySqrt(x: float) -> float:
        ...
    ```

    Args:
        processor (Optional[Callable[[ObjectStream[W], ast.Call],
                  Tuple[ObjectStream[W], ast.AST]]], optional): [description]. Defaults to None.
    '''
    # TODO: Do we really need to register this inside the decorator? Can we just register
    #       and return the function?
    def decorate(function: Callable):
        register_func_adl_function(function, processor)
        return function

    return decorate


def _find_keyword(keywords: List[ast.keyword], name: str) \
        -> Tuple[Optional[ast.AST], List[ast.keyword]]:
    '''Find an argument in a keyword list.

    Returns:
        [type]: The argument or None if not found.
    '''
    for kw in keywords:
        if kw.arg == name:
            new_kw = list(keywords)
            new_kw.remove(kw)
            return kw.value, new_kw
    return None, keywords


# Some functions to enable backwards compatibility.
# Capability may be degraded in older versions - particularly 3.6.
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
        return getattr(tp, "__args__", ())


@dataclass
class CollectionClassInfo:
    'Info for a collection class'
    obj_type: Type


_g_collection_classes: Dict[Type, CollectionClassInfo] = {}


C_TYPE = TypeVar('C_TYPE')


def register_func_adl_os_collection(c: C_TYPE) -> C_TYPE:
    '''Register a func_adl collections

    Args:
        c (type): Class to register

    Returns:
        [type]: [description]
    '''
    _g_collection_classes[c] = CollectionClassInfo(c)
    return c


StreamItem = TypeVar('StreamItem')


@register_func_adl_os_collection
class ObjectStreamInternalMethods(ObjectStream[StreamItem]):
    '''There are a number of methods and manipulations that are not
    available at the event level, but are at the collection level. For default
    behavior, we collect those here.

    If you have a custom type for your collections, it would probably be easiest to
    in inherit from this and add your own custom methods on top of this.

    Note that these methods are *never* called. The key part of this is following
    the `item_type` through!! This is because this package does not yet know how
    to follow generics in python at runtime (think of this as poor man's type resolution).
    '''
    def __init__(self, a: ast.AST, item_type: Type):
        super().__init__(a, item_type)

    @property
    def item_type(self) -> Type:
        return self._item_type

    def First(self) -> StreamItem:
        return self.item_type

    def Count(self) -> int:
        ...

    # TODO: Add all other items that belong here


def _load_g_collection_classes():
    'Use for testing to reset a global collection'
    register_func_adl_os_collection(ObjectStreamInternalMethods)


def func_adl_callback(
        callback: Callable[[ObjectStream[StreamItem], ast.Call],
                           Tuple[ObjectStream[StreamItem], ast.Call]]):
    # TODO: Add something here to describe how to use this
    def decorator(cls: C_TYPE) -> C_TYPE:
        cls._func_adl_type_info = callback  # type: ignore
        return cls
    return decorator


def _fill_in_default_arguments(func: Callable, call: ast.Call) -> Tuple[ast.Call, Type]:
    '''Given a call and the function definition:

    * Defaults are filled in
    * A keyword argument that is positional is moved to the end
    * A follower is left to the original to help with recovering modifications to
      nested expressions.

    Args:
        func (Callable): The function definition
        call (ast.Call): The ast call site to be modified

    Raises:
        ValueError: Missing arguments, etc.

    Returns:
        Tuple[ast.Call, Type]: The modified call site and return type.
    '''
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

    # If we are making a change to the call, put in a reference back to the
    # original call.
    if len(arg_array) != len(call.args):
        old_call_ast = call
        call = copy.copy(call)
        call.args = arg_array
        call.keywords = keywords
        call._old_ast = old_call_ast  # type: ignore

    # Mark the return type - especially if it is missing
    t_info = typing.get_type_hints(func)
    return_type = Any
    if 'return' in t_info:
        return_type = t_info['return']
    else:
        logging.getLogger(__name__).warning(f'Missing return annotation for {func.__name__}'
                                            ' - assuming Any')
        return_type = Any

    return call, return_type


def fixup_ast_from_modifications(transformed_ast: ast.AST, original_ast: ast.Call) -> ast.Call:
    'Update the ast, if needed, with modifications'

    class arg_fixer(ast.NodeVisitor):
        def __init__(self, old_copy):
            self._old_copy = old_copy
            self._new_copy = None

        @property
        def redone_ast(self) -> ast.Call:
            if self._new_copy is not None:
                return self._new_copy
            assert self._old_copy is not None
            return self._old_copy

        def _update_copy(self):
            if self._new_copy is None:
                self._new_copy = copy.copy(self._old_copy)
                self._old_copy = None

        def visit_Call(self, node: ast.Call):
            self.generic_visit(node)
            orig_ast = getattr(node, '_old_ast', None)
            if orig_ast is None:
                return node

            self._update_copy()
            n_old_args = len(orig_ast.args)
            for a in node.args[n_old_args:]:
                orig_ast.args.append(a)

    fixer = arg_fixer(original_ast)
    fixer.visit(transformed_ast)
    return fixer.redone_ast


T = TypeVar('T')


def remap_by_types(o_stream: ObjectStream[T], var_name: str, var_type: Any, a: ast.AST) \
        -> Tuple[ObjectStream[T], ast.AST, Type]:
    '''Remap a call by a type. Given the type of `var_name` it will do its best
    to follow the objects types through the expression.

    Note:
      * Complex expressions are not supported, like addition, etc.
      * Method calls are well followed
      * This isn't a complete type follower, unfortunately.

    Raises:
        ValueError: Forgotten arguments, etc.

    Returns:
        ObjectStream[T]
        ast: Updated stream and call site with
        Type: The return type of the expression given. `Any` means it couldn't
    '''
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

        def lookup_type(self, name: Union[str, object]) -> Type:
            'Return the type for a node, Any if we do not know about it'
            return self._found_types.get(name, Any)

        def process_method_call_on_stream_obj(self, obj_info: CollectionClassInfo,
                                              call_method_name: str,
                                              call_node: ast.Call,
                                              item_type: type
                                              ) \
                -> Optional[Tuple[ast.AST, Any]]:
            '''The type following and resolution system in func_adl is pretty limited.
            When it fails, we fall back to try another method - basically, someone providing
            dummy classes that implement an `ObjectStream` like interface:
                `object_stream.query_ast`
                `object_stream.item_type`

            They are expected to build new versions of themselves much like `object_stream`.

            The reason they are here is that the API for event level is different than for
            object level. For example, `First` is defined not to make sense at the event level,
            but it very much makes sense at the object level. This provides a way to track
            the types through those calls.

            Returns:
                None if we can't figure out what to do here
                (updated call site, return annotation)
                Return annotation is replaced with the original object (e.g. Iterable)
                if that is what is started out as.
            '''
            # Create the object and grab the method. This is where the API
            # of the dummy object comes into play
            s = obj_info.obj_type(ast.Name('basic'), item_type)
            call_method = getattr(s, call_method_name, None)
            assert call_method is not None

            # Call it. We can only deal with a single argument here...
            if len(call_node.args) == 0:
                r = call_method()
            elif len(call_node.args) == 1:
                r = call_method(call_node.args[0])
            else:
                return None

            # Make sure we have the right type
            if hasattr(r, "query_ast"):
                def add_md(md: ast.arg):
                    self._stream = self._stream.MetaData(ast.literal_eval(md))
                scan_for_metadata(r.query_ast, add_md)
                call_node = fixup_ast_from_modifications(r.query_ast, call_node)
                return call_node, Iterable[r.item_type]  # type: ignore
            return call_node, type(r)

        def process_method_call_on_type(self, m_name: str, node: ast.Call, obj_type: type) \
                -> Optional[Tuple[ast.AST, Any]]:
            '''Process the method call against the type `obj_type`. We do method lookup
            and first try simple type following. If that fails, we move onto ObjectStream
            methods (which are a hack!).

            Returns:
                - None if we can't figure out the method call
                - Tuple of the class site and the return type information if we can.
            '''
            # Get method and its attached class
            call_method_info = get_method_and_class(obj_type, m_name)
            if call_method_info is None:
                return None
            call_method_class, call_method = call_method_info

            # Fill in default arguments next. This might update the call site, and
            # it will also get us any return annotation information.
            r_node, return_annotation_raw = _fill_in_default_arguments(call_method, node)

            # Get back all the TypeVar's this guy has on it.
            return_annotation = resolve_type_vars(return_annotation_raw, obj_type,
                                                  at_class=call_method_class)

            # If we failed with simple type resolution here, then there is something
            # more complex going on. For example, the return type depends on a lambda
            # function (for example, the lambda function in the `Select` method).
            if return_annotation is None and (get_origin(obj_type) in _g_collection_classes):
                return self.process_method_call_on_stream_obj(
                    _g_collection_classes[get_origin(obj_type)],
                    m_name, node, get_args(obj_type)[0])

            # See if there is a call-back to process the call on the
            # object or the function
            for base_obj in [obj_type, call_method]:
                attr = getattr(base_obj, '_func_adl_type_info', None)
                if attr is not None:
                    r_stream, r_node = attr(self.stream, r_node)
                    assert isinstance(r_node, ast.AST)
                    self._stream = r_stream

            return (r_node, return_annotation)

        def process_method_call(self, node: ast.Call, obj_type: type) -> ast.AST:
            # Make reference copies that we'll populate as we go
            r_node = node

            # Deal with default arguments and the method signature
            #  - Could be a method on the object we are looking at
            #  - If it is a collection, could be First, Select, etc.
            try:
                assert isinstance(r_node.func, ast.Attribute), \
                        f"Only method named calls are supported {ast.dump(r_node.func)}"

                r_result = self.process_method_call_on_type(r_node.func.attr, r_node, obj_type)

                if r_result is None and is_iterable(obj_type):
                    # This could be a method call against one of the ObjectStream like
                    # classes. All these are wrapers around an item. So `obj_type` should
                    # be a sequence of some sort - of an item type.
                    item_type = unwrap_iterable(obj_type)

                    # Loop over all the possible object stream like objects we know
                    # about
                    for c in _g_collection_classes:
                        r_result = self.process_method_call_on_type(r_node.func.attr, r_node,
                                                                    c[item_type])
                        if r_result is not None:
                            break

                if r_result is None:
                    self._found_types[node] = Any
                    if obj_type != Any:
                        logging.getLogger(__name__).warning(f'Function {r_node.func.attr} not '
                                                            f'found on object {obj_type}')
                    return r_node

                r_node, return_annotation = r_result

                # And if we have a return annotation, then we should record it!
                self._found_types[r_node] = return_annotation
                self._found_types[node] = return_annotation

                return r_node
            except Exception as e:
                f_name = node.func.attr  # type: ignore
                raise ValueError(f'Error processing method call {f_name} on '
                                 f'class {get_class_name(obj_type)} ({str(e)}).') from e

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
                self._found_types[node] = return_annotation

                return r_node
            except Exception as e:
                raise ValueError(f'Error processing function call {node} on '
                                 f'function {func_info.function.__name__} ({str(e)})') from e

        def visit_Call(self, node: ast.Call) -> ast.AST:
            t_node = self.generic_visit(node)
            assert isinstance(t_node, ast.Call)
            if isinstance(t_node.func, ast.Attribute):
                # Do we know the type of the value?
                found_type = self.lookup_type(t_node.func.value)
                if found_type is not None:
                    t_node = self.process_method_call(t_node, found_type)
            elif isinstance(t_node.func, ast.Name):
                if t_node.func.id in _global_functions:
                    t_node = self.process_function_call(t_node, _global_functions[t_node.func.id])
            return t_node

        def visit_Lambda(self, node: ast.Lambda) -> Any:
            'Prevent looking into a lambda until we actually call it'
            self._found_types[node] = Callable
            return node

        def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
            t_node = self.generic_visit(node)
            self._found_types[node] = self._found_types[node.operand]
            self._found_types[t_node] = self._found_types[node.operand]
            return t_node

        def visit_BinOp(self, node: ast.BinOp) -> Any:
            t_node = super().generic_visit(node)
            assert isinstance(t_node, ast.BinOp)
            t_left = self.lookup_type(t_node.left)
            t_right = self.lookup_type(t_node.right)

            if (t_left == Any) or (t_right == Any):
                self._found_types[node] = Any
                self._found_types[t_node] = Any
            elif (t_left == float) or (t_right == float):
                self._found_types[node] = float
                self._found_types[t_node] = float
            elif isinstance(node.op, ast.Div):
                self._found_types[node] = float
                self._found_types[t_node] = float
            else:
                self._found_types[node] = int
                self._found_types[t_node] = int

            return t_node

        def visit_BoolOp(self, node: ast.BoolOp) -> Any:
            t_node = super().generic_visit(node)
            self._found_types[node] = bool
            self._found_types[t_node] = bool

            return t_node

        def visit_Compare(self, node: ast.Compare) -> Any:
            t_node = self.generic_visit(node)
            self._found_types[node] = bool
            self._found_types[t_node] = bool
            return t_node

        def visit_IfExp(self, node: ast.IfExp) -> Any:
            t_node = self.generic_visit(node)
            assert isinstance(t_node, ast.IfExp)
            t_true = self.lookup_type(t_node.body)
            t_false = self.lookup_type(t_node.orelse)

            final_type = Any
            if t_true == t_false:
                final_type = t_true
            elif t_true in [int, float] and t_false in [int, float]:
                final_type = float
            else:
                raise ValueError(f'IfExp branches have different types: {t_true} and {t_false}'
                                 ' - must be compatible')
            self._found_types[node] = final_type
            self._found_types[t_node] = final_type
            return t_node

        def visit_Subscript(self, node: ast.Subscript) -> Any:
            t_node = self.generic_visit(node)
            assert isinstance(t_node, ast.Subscript)
            inner_type = unwrap_iterable(self.lookup_type(t_node.value))
            self._found_types[node] = inner_type
            self._found_types[t_node] = inner_type
            return t_node

        def visit_Name(self, node: ast.Name) -> ast.Name:
            if node.id in self._found_types:
                self._found_types[node] = self._found_types[node.id]
            elif node.id in _global_functions:
                self._found_types[node] = Callable
            else:
                logging.getLogger(__name__).warning(f'Unknown type for name {node.id}')
                self._found_types[node] = Any
            return node

        def visit_Constant(self, node: ast.Constant) -> Any:
            self._found_types[node] = type(node.value)
            return node

        def visit_Num(self, node: ast.Num) -> Any:  # pragma: no cover
            '3.7 compatability'
            self._found_types[node] = type(node.n)
            return node

        def visit_Str(self, node: ast.Str) -> Any:  # pragma: no cover
            '3.7 compatability'
            self._found_types[node] = str
            return node

        def visit_NameConstant(self, node: ast.NameConstant) -> Any:  # pragma: no cover
            '3.7 compatability'
            if node.value is None:
                raise ValueError('Do not know how to work with pythons None')
            self._found_types[node] = bool
            return node

    tt = type_transformer(o_stream)
    r_a = tt.visit(a)

    return tt.stream, r_a, tt.lookup_type(a)


def remap_from_lambda(o_stream: ObjectStream[T], l_func: ast.Lambda) \
        -> Tuple[ObjectStream[T], ast.Lambda, Type]:
    '''Helper function that will translate the contents of lambda
    function with inline methods and special functions.

    Returns:
        ObjectStream[T]
        ast.AST: Updated stream and lambda function
        Type: Return type of the lambda function, Any if not known.
    '''
    assert len(l_func.args.args) == 1
    orig_type = o_stream.item_type
    var_name = l_func.args.args[0].arg
    stream, new_body, return_type = remap_by_types(o_stream, var_name, orig_type, l_func.body)
    return stream, ast.Lambda(l_func.args, new_body), return_type
