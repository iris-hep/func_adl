from __future__ import annotations

import ast
import copy
import inspect
import logging
import sys
from dataclasses import dataclass, make_dataclass
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    get_type_hints,
)

from .object_stream import ObjectStream
from .util_ast import as_literal, scan_for_metadata
from .util_types import (
    get_args,
    get_method_and_class,
    get_origin,
    is_iterable,
    resolve_type_vars,
    unwrap_iterable,
)

# Internal named tuple containing info for a global function
# definitions. Functions with these names can be used inline
# in func_adl expressions, and will trigger the processor and
# also be subject to normal argument resolution.
U = TypeVar("U")
_FuncAdlFunction = NamedTuple(
    "_FuncAdlFunction",
    [
        ("name", str),
        ("function", Callable),
        (
            "processor_function",
            Optional[
                Callable[
                    [ObjectStream[U], ast.Call], Tuple[ObjectStream[U], ast.AST]  # type: ignore
                ]
            ],
        ),
    ],
)
_global_functions: Dict[str, _FuncAdlFunction] = {}


def _load_default_global_functions():
    "Define the python standard functions that map straight through"
    # TODO: Add in other functions

    def my_abs(x: float) -> float: ...  # noqa

    _global_functions["abs"] = _FuncAdlFunction("abs", my_abs, None)


_load_default_global_functions()


V = TypeVar("V")


def register_func_adl_function(
    function: Callable,
    processor_function: Optional[
        Callable[[ObjectStream[V], ast.Call], Tuple[ObjectStream[V], ast.AST]]
    ],
) -> None:
    """Register a new function for use inside a func_adl expression.

    * A function registered will have its arguments filled in - defaults,
    keywords converted to positional, etc.
    * If a processor function is provided, it will be called as the call
    site si being examined. Any bit can be modified.

    Args:
        function (Callable): The type definition for the function (type st)
        processor_function (Callable[[ObjectStream[T], ast.Call],
            Tuple[ObjectStream[T], ast.AST]]):
            The processor function that can modify the stream, etc.
    """
    info = _FuncAdlFunction(function.__name__, function, processor_function)  # type: ignore
    _global_functions[info.name] = info


W = TypeVar("W")


def func_adl_callable(
    processor: Optional[
        Callable[[ObjectStream[W], ast.Call], Tuple[ObjectStream[W], ast.AST]]
    ] = None
):
    """Dectorator that will declare a function that can be used inline in
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
    """

    # TODO: Do we really need to register this inside the decorator? Can we just register
    #       and return the function?
    def decorate(function: Callable):
        register_func_adl_function(function, processor)
        return function

    return decorate


def _find_keyword(
    keywords: List[ast.keyword], name: str
) -> Tuple[Optional[ast.AST], List[ast.keyword]]:
    """Find an argument in a keyword list.

    Returns:
        [type]: The argument or None if not found.
    """
    for kw in keywords:
        if kw.arg == name:
            new_kw = list(keywords)
            new_kw.remove(kw)
            return kw.value, new_kw
    return None, keywords


# Some functions to enable backwards compatibility.
# Capability may be degraded in older versions.
if sys.version_info >= (3, 8):  # pragma: no cover

    def get_type_args(tp):
        import typing

        return typing.get_args(tp)

else:  # pragma: no cover

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
    "Info for a collection class"
    obj_type: Type


_g_collection_classes: Dict[Type, CollectionClassInfo] = {}


StreamItem = TypeVar("StreamItem")


@dataclass
class PropertyCallbackInfo(Generic[StreamItem]):
    "Info for a property parameterized callback"

    # Callback
    callback: Callable[
        [ObjectStream[StreamItem], ast.Call, Any], Tuple[ObjectStream[StreamItem], ast.Call, Type]
    ]


_g_parameterized_callbacks: Dict[property, PropertyCallbackInfo] = {}


C_TYPE = TypeVar("C_TYPE")


def register_func_adl_os_collection(c: C_TYPE) -> C_TYPE:
    """Register a func_adl collections

    Args:
        c (type): Class to register

    Returns:
        [type]: [description]
    """
    _g_collection_classes[c] = CollectionClassInfo(c)  # type: ignore
    return c


@register_func_adl_os_collection
class ObjectStreamInternalMethods(ObjectStream[StreamItem]):
    """There are a number of methods and manipulations that are not
    available at the event level, but are at the collection level. For default
    behavior, we collect those here.

    If you have a custom type for your collections, it would probably be easiest to
    in inherit from this and add your own custom methods on top of this.

    Note that these methods are *never* called. The key part of this is following
    the `item_type` through!! This is because this package does not yet know how
    to follow generics in python at runtime (think of this as poor man's type resolution).
    """

    def __init__(self, a: ast.AST, item_type: Union[Type, object]):
        super().__init__(a, item_type)  # type: ignore

    @property
    def item_type(self) -> Type:
        return self._item_type

    def First(self) -> StreamItem:
        return self.item_type  # type: ignore

    def Count(self) -> int: ...  # noqa

    # TODO: Add all other items that belong here


def _load_g_collection_classes():
    "Use for testing to reset a global collection"
    register_func_adl_os_collection(ObjectStreamInternalMethods)


def func_adl_callback(
    callback: Callable[
        [ObjectStream[StreamItem], ast.Call], Tuple[ObjectStream[StreamItem], ast.Call]
    ]
):
    """Decorator to use on either classes or class methods that participate
    in `func_adl` queries. As these classes are traversed by the `func-adl`
    query, the given callback will be called.

    This allows the system to inject `MetaData` and other things into the query
    stream modifying the query on the fly.

    - If applied at the class level, the call back will be invoked any time any
      method is invoked on this class
    - If applied at the method level, when the method is invoked it will be applied.
    - If applied at both levels, the class level callback will be invoked first.

    Args:
        callback (Callable[[ObjectStream[StreamItem], ast.Call],
            Tuple[ObjectStream[StreamItem], ast.Call]]): Callback when object or function is used.
    """

    def decorator(cls: C_TYPE) -> C_TYPE:
        cls._func_adl_type_info = callback  # type: ignore
        return cls

    return decorator


TProp = TypeVar("TProp")


def func_adl_parameterized_call(
    cb: Callable[
        [ObjectStream[StreamItem], ast.Call, Any], Tuple[ObjectStream[StreamItem], ast.Call, Type]
    ]
) -> Callable[[TProp], TProp]:
    """Mark a property access to be treated as a parameterized callback, with `cb` being called
    when the callback is detected. The parameters from the slice operations are passed to the
    callback, but removed from the AST.

    ```python
    jet.getAttribute[cpp_float]('my_attrib')
    ```

    Gets transformed to `jet.getAttribute('my_attrib')`, and then `cb` is called with the current
    stream object (so `MetaData` can be added), the transformed ast (so it can be modified if
    desired), and `cpp_float`.

    The callback must return the updated stream, the updated (or not) ast, and the resulting type
    from the call (like `float`).

    Args:
        cb (Callable[ [ObjectStream[StreamItem], ast.Call, Any],
            Tuple[ObjectStream[StreamItem], ast.Call, Type] ]):
            The callback to be invoked when this node is found in the ast.

    Returns:
        Callable[[TProp], TProp]: Decorator function to capture a property object.
    """

    def decorator(c: TProp) -> TProp:
        if not isinstance(c, property):
            raise ValueError(f"Parameterized methods must start with proper definition ({c})")
        _g_parameterized_callbacks[c] = PropertyCallbackInfo(cb)
        return c

    return decorator


def _fill_in_default_arguments(func: Callable, call: ast.Call) -> Tuple[ast.Call, Type]:
    """Given a call and the function definition:

    * Defaults are filled in
    * A keyword argument that is positional is moved to the end
    * A follower is left to the original to help with recovering modifications to
      nested expressions.

    # TODO: Use python's signature bind to do this:
    #   https://docs.python.org/3/library/inspect.html#inspect.Signature.bind)

    Args:
        func (Callable): The function definition
        call (ast.Call): The ast call site to be modified

    Raises:
        ValueError: Missing arguments, etc.

    Returns:
        Tuple[ast.Call, Type]: The modified call site and return type.
    """
    sig = inspect.signature(func)
    i_arg = 0
    arg_array = list(call.args)
    keywords = list(call.keywords)
    for param in sig.parameters.values():
        if param.name != "self":
            if len(arg_array) <= i_arg:
                # See if they specified it as a keyword
                a, keywords = _find_keyword(keywords, param.name)
                if a is not None:
                    arg_array.append(a)  # type: ignore
                elif param.default is not param.empty:
                    a = as_literal(param.default)
                    arg_array.append(a)
                else:
                    raise ValueError(f"Argument {param.name} is required")

    # If we are making a change to the call, put in a reference back to the
    # original call.
    if len(arg_array) != len(call.args):
        old_call_ast = call
        call = copy.copy(call)
        call.args = arg_array
        call.keywords = keywords
        call._old_ast = old_call_ast  # type: ignore

    # Mark the return type - especially if it is missing
    t_info = get_type_hints(func)
    return_type = Any
    if "return" in t_info:
        return_type = t_info["return"]
    else:
        logging.getLogger(__name__).warning(
            f"Missing return annotation for {func.__name__}" " - assuming Any"
        )
        return_type = Any

    return call, return_type


def fixup_ast_from_modifications(transformed_ast: ast.AST, original_ast: ast.Call) -> ast.Call:
    "Update the ast, if needed, with modifications"

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
            orig_ast = getattr(node, "_old_ast", None)
            if orig_ast is None:
                return node

            self._update_copy()
            n_old_args = len(orig_ast.args)
            for a in node.args[n_old_args:]:
                orig_ast.args.append(a)
            orig_ast.func = node.func

    fixer = arg_fixer(original_ast)
    fixer.visit(transformed_ast)
    return fixer.redone_ast


@dataclass
class _MethodObjectCandidate:
    """Candidate object for a particular call"""

    # The object type the method is actually getting called on
    obj_type: type

    # The object the method is defined on
    # In case of inheritance this is different than above
    method_class: type

    # The method itself
    method: Callable


@dataclass
class _MethodTypeReturnInfo:
    """For a particular method call, the return info"""

    # Update version of the ast
    node: ast.Call

    # Return type
    return_type: Union[Type, object]

    # If full type resolution was done (e.g. lambda following), or
    # if there were no lambda arguments to follow.
    full_type_resolution: bool

    # The object we actually did the call against
    obj_info: Optional[_MethodObjectCandidate]


T = TypeVar("T")


def remap_by_types(
    o_stream: ObjectStream[T], var_name: str, var_type: Any, a: ast.AST
) -> Tuple[ObjectStream[T], ast.AST, Type]:
    """Remap a call by a type. Given the type of `var_name` it will do its best
    to follow the objects types through the expression.

    Note:
      * Complex expressions are supported, like addition, etc.
      * Method calls are well followed
      * This isn't a complete type follower, unfortunately.

    Raises:
        ValueError: Forgotten arguments, etc.

    Returns:
        ObjectStream[T]
        ast: Updated stream and call site with
        Type: The return type of the expression given. `Any` means it couldn't
    """
    S = TypeVar("S")

    class type_transformer(ast.NodeTransformer, Generic[S]):
        def __init__(self, o_stream: ObjectStream[S]):
            self._stream = o_stream
            self._found_types: Dict[Union[str, object], Union[type, object]] = {var_name: var_type}

        @property
        def stream(self) -> ObjectStream[S]:
            return self._stream  # type: ignore

        def lookup_type(self, name: Union[str, object]) -> Type:
            "Return the type for a node, Any if we do not know about it"
            t = self._found_types.get(name, None)
            if t is not None:
                return t  # type: ignore
            if not isinstance(name, ast.AST):
                return Any  # type: ignore

            # It could be we can determine the type from this ast.
            return Any  # type: ignore

            return t  # type: ignore

        def process_method_call_on_stream_obj(
            self,
            obj_info: CollectionClassInfo,
            call_method_name: str,
            call_node: ast.Call,
            item_type: type,
        ) -> Optional[Tuple[ast.AST, Any]]:
            """The type following and resolution system in func_adl is pretty limited.
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
            """
            # Create the object and grab the method. This is where the API
            # of the dummy object comes into play
            s = obj_info.obj_type(ast.Name("basic"), item_type)
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

            return call_node, r

        def type_follow_in_callbacks(
            self, m_name: str, call_site_info: _MethodObjectCandidate, r_node: ast.Call
        ) -> Optional[_MethodTypeReturnInfo]:
            """If this method has any callbacks, follow them to update the stream
            and ast.

            Args:
                m_name (str): The name of hte method
                call_site_info (_MethodObjectCandidate): Method information (obj, etc.)
                r_node (ast.Call): The call site in the ast

            Returns:
                Optional[_MethodTypeReturnInfo]: If we can do type following, the results
            """
            # Next, we need to figure out what the return type is. There are multiple
            # ways, unfortunately, that we can get the return-type. We might be able to
            # do simple type resolution, but we might also have to depend on call-backs to
            # figure out what is going on (think of the Select call where the lambda return
            # type tells us the type of return of Select)

            # If this is a known collection class, we can use call-backs to follow it.
            if get_origin(call_site_info.obj_type) in _g_collection_classes:
                rtn_value = self.process_method_call_on_stream_obj(
                    _g_collection_classes[get_origin(call_site_info.obj_type)],
                    m_name,
                    r_node,
                    get_args(call_site_info.obj_type)[0],
                )
                if rtn_value is not None:
                    new_a, new_return_annotation = rtn_value
                    assert isinstance(new_a, ast.Call)
                    return _MethodTypeReturnInfo(
                        node=new_a,
                        return_type=new_return_annotation,
                        full_type_resolution=True,
                        obj_info=call_site_info,
                    )

            return None

        def process_method_callbacks(self, obj_type: type, node: ast.AST, call_method) -> ast.Call:
            """Call any callbacks that the object has registered. This might change
            the ast.

            Args:
                obj_type (type): The type of the object
                node (ast.AST): The ast node of the call site
                call_method (_type_): The method. This is the method that was called

            Returns:
                ast.AST: The updated (or not) ast.
            """
            for base_obj in [obj_type, call_method]:
                attr = getattr(base_obj, "_func_adl_type_info", None)
                if attr is not None:
                    r_stream, node = attr(self.stream, node)
                    assert isinstance(node, ast.AST)
                    self._stream = r_stream

            assert isinstance(node, ast.Call)
            return node

        def process_method_call(self, node: ast.Call, obj_type: type) -> ast.AST:
            """Manage a call against a typed object.

            1. Fill in default arguments based on the signature from the object type.
            1. Insert metadata into the stream if there are call backs based on the object type.
            1. Type follow the call site to get the return type, and to make sure anything inside
               lambda's etc., get correctly type followed as well.

            Args:
                node (ast.Call): The ast node
                obj_type (type): The object type this method call is occuring against

            Returns:
                ast.AST: An updated ast that is the new method call (with default args, etc.)
            """
            # Make reference copies that we'll populate as we go
            r_node = node

            # Find all objects that this method exists on.
            base_obj_list_all = [obj_type]
            if is_iterable(obj_type):
                item_type = unwrap_iterable(obj_type)
                base_obj_list_all += [c[item_type] for c in _g_collection_classes]

            assert isinstance(r_node.func, ast.Attribute)
            m_name = r_node.func.attr

            base_obj_list: List[_MethodObjectCandidate] = []
            for bo in base_obj_list_all:
                call_method_info = get_method_and_class(bo, m_name)
                if call_method_info is not None:
                    call_method_class, call_method = call_method_info
                    base_obj_list.append(
                        _MethodObjectCandidate(
                            obj_type=bo, method_class=call_method_class, method=call_method
                        )
                    )

            # For each definition try to get typing results out of it.
            # Take the base possible one.
            return_results: List[_MethodTypeReturnInfo] = []
            for base_obj in base_obj_list:
                # Do basic static analysis without doing any call backs.
                default_args_node, return_annotation_raw = _fill_in_default_arguments(
                    base_obj.method, r_node
                )
                return_annotation = resolve_type_vars(
                    return_annotation_raw, base_obj.obj_type, at_class=base_obj.method_class
                )

                # if the static type check worked, we might be able to use this answer.
                if return_annotation is not None:
                    has_lambda_arg = any(isinstance(a, ast.Lambda) for a in default_args_node.args)
                    return_results.append(
                        _MethodTypeReturnInfo(
                            node=default_args_node,
                            return_type=return_annotation,
                            full_type_resolution=not has_lambda_arg,
                            obj_info=base_obj,
                        )
                    )

                # If we need to do full type following, then we should do that now.
                if len(return_results) == 0 or not return_results[-1].full_type_resolution:
                    r_result = self.type_follow_in_callbacks(m_name, base_obj, default_args_node)
                    if r_result is not None:
                        return_results.append(r_result)

                # If we have a good answer, we can skip all this next stuff.
                if len(return_results) > 0 and return_results[-1].full_type_resolution:
                    break

            # If we got nothing, then we really do not know what is going on.
            if len(return_results) == 0:
                if obj_type != Any:
                    self._found_types[node] = Any
                    logging.getLogger(__name__).warning(
                        f"Method {r_node.func.attr} not " f"found on object {obj_type}"
                    )
                return_results.append(
                    _MethodTypeReturnInfo(
                        node=r_node, return_type=Any, full_type_resolution=True, obj_info=None
                    )
                )

            # See if we fully processed the call. If not, and there is a lambda, then
            # we need a warning here.
            if not any(r.full_type_resolution for r in return_results):
                if any(isinstance(a, ast.Lambda) for a in r_node.args):  # type: ignore
                    logging.getLogger(__name__).warning(
                        f"Lambda argument in {m_name} was not type followed. Class"
                        f" containing {m_name} should be corrected."
                    )

            # Next, we'll do type resolution here
            best_result = return_results[-1]
            if best_result.obj_info is not None:
                best_result.node = self.process_method_callbacks(
                    best_result.obj_info.obj_type, best_result.node, best_result.obj_info.method
                )

            # We'll pick off the first one in this case.
            r_node, return_annotation = best_result.node, best_result.return_type

            # And if we have a return annotation, then we should record it!
            self._found_types[r_node] = return_annotation
            self._found_types[node] = return_annotation

            return r_node

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
                raise ValueError(
                    f"Error processing function call {node} on "
                    f"function {func_info.function.__name__} ({str(e)})"
                ) from e

        def process_paramaterized_method_call(
            self,
            node: ast.Call,
            obj_type: Type,
            attr_name: str,
            slice: ast._SliceT,  # type: ignore
            func: ast.Attribute,
        ) -> ast.Call:
            "Process a obj.method[param, param, ...](args) style call"
            # Fetch property, make sure it has info attached to it
            prop = getattr(obj_type, attr_name)
            callback_info = _g_parameterized_callbacks.get(prop, None)
            if callback_info is None:
                raise ValueError(
                    f'Property "{obj_type}{attr_name}" was not decorated with '
                    "func_adl_parameterize d_call. Malformed object or usage."
                )

            # Get the parameters from the subscript
            if isinstance(slice, ast.Index):
                parameters = ast.literal_eval(slice.value)  # type: ignore
            else:
                parameters = ast.literal_eval(slice)

            # rebuild the expression, removing the slice operation and turning this into a
            # "normal" call.
            t_node = ast.Call(func, node.args, node.keywords)

            # Run the callback processing
            r_stream, r_node, return_type = callback_info.callback(self.stream, t_node, parameters)
            self._stream = r_stream

            # Mark this ast with the fact we've updated it.
            # TODO: Make sure this is done (and tested) for all aspects of the different
            #       types of function calls (functions, regular methods, etc.)
            r_node._old_ast = node  # type: ignore

            self._found_types[r_node] = return_type
            self._found_types[node] = return_type

            return r_node

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
            elif isinstance(t_node.func, ast.Subscript):
                if isinstance(t_node.func.value, ast.Attribute):
                    found_type = self.lookup_type(t_node.func.value.value)
                    if found_type is not None:
                        t_node = self.process_paramaterized_method_call(
                            t_node,
                            found_type,
                            t_node.func.value.attr,
                            t_node.func.slice,
                            t_node.func.value,
                        )
            return t_node

        def visit_Lambda(self, node: ast.Lambda) -> Any:
            "Prevent looking into a lambda until we actually call it"
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
            elif t_true in [int, float, Any] and t_false in [int, float, Any]:
                final_type = float
            else:
                raise ValueError(
                    f"IfExp branches have different types: {t_true} and {t_false}"
                    " - must be compatible"
                )
            self._found_types[node] = final_type
            self._found_types[t_node] = final_type
            return t_node

        def visit_Subscript(self, node: ast.Subscript) -> Any:
            t_node = self.generic_visit(node)
            assert isinstance(t_node, ast.Subscript)
            if isinstance(t_node.value, ast.Tuple):
                slice = t_node.slice
                # This if statement can be removed when we no longer support 3.8.
                if isinstance(slice, ast.Index):
                    slice = slice.value  # type: ignore
                if not isinstance(slice, ast.Constant):
                    raise ValueError(
                        f"Slices must be indexable constants only - {ast.dump(slice)} is not "
                        "valid."
                    )
                index = slice.value
                if len(t_node.value.elts) <= index:
                    raise ValueError(f"Index {index} out of range for {ast.dump(node.value)}")
                self._found_types[node] = self.lookup_type(t_node.value.elts[index])
                self._found_types[t_node] = self.lookup_type(t_node.value.elts[index])
            else:
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
                logging.getLogger(__name__).warning(f"Unknown type for name {node.id}")
                self._found_types[node] = Any
            return node

        def visit_Dict(self, node: ast.Dict) -> Any:
            t_node = self.generic_visit(node)
            assert isinstance(t_node, ast.Dict)

            fields: List[Tuple[str, type]] = [
                (ast.literal_eval(f), self.lookup_type(v))  # type: ignore
                for f, v in zip(t_node.keys, t_node.values)
            ]
            dict_dataclass = make_dataclass("dict_dataclass", fields)

            self._found_types[t_node] = dict_dataclass
            return t_node

        def visit_Constant(self, node: ast.Constant) -> Any:
            self._found_types[node] = type(node.value)
            return node

        def visit_Num(self, node: ast.Num) -> Any:  # pragma: no cover
            "3.7 compatability"
            self._found_types[node] = type(node.n)
            return node

        def visit_Str(self, node: ast.Str) -> Any:  # pragma: no cover
            "3.7 compatability"
            self._found_types[node] = str
            return node

        def visit_NameConstant(self, node: ast.NameConstant) -> Any:  # pragma: no cover
            "3.7 compatability"
            if node.value is None:
                raise ValueError("Do not know how to work with pythons None")
            self._found_types[node] = bool
            return node

        def visit_Attribute(self, node: ast.Attribute) -> Any:
            t_node = self.generic_visit(node)
            assert isinstance(t_node, ast.Attribute)
            # If this is a dict reference, then figure out what the
            # type is for that value of the dict.
            if isinstance(t_node.value, ast.Dict):
                key = t_node.attr
                key_index = [
                    e for e, k in enumerate(t_node.value.keys) if k.value == key  # type: ignore
                ]
                if len(key_index) == 0:
                    raise ValueError(f"Key {key} not found in dict expression!!")
                value = t_node.value.values[key_index[0]]
                self._found_types[node] = self.lookup_type(value)
            return t_node

    tt = type_transformer(o_stream)
    r_a = tt.visit(a)

    return tt.stream, r_a, tt.lookup_type(a)


def remap_from_lambda(
    o_stream: ObjectStream[T], l_func: ast.Lambda
) -> Tuple[ObjectStream[T], ast.Lambda, Type]:
    """Helper function that will translate the contents of lambda
    function with inline methods and special functions.

    Returns:
        ObjectStream[T]
        ast.AST: Updated stream and lambda function
        Type: Return type of the lambda function, Any if not known.
    """
    assert len(l_func.args.args) == 1
    orig_type = o_stream.item_type
    var_name = l_func.args.args[0].arg
    stream, new_body, return_type = remap_by_types(o_stream, var_name, orig_type, l_func.body)
    return stream, ast.Lambda(l_func.args, new_body), return_type


def reset_global_functions():
    """Resets all the global functions we know about.

    Generally only used between tests.
    """
    global _global_functions, _g_collection_classes, _g_parameterized_callbacks
    _global_functions = {}
    _load_default_global_functions()
    _g_collection_classes = {}
    _load_g_collection_classes()
    _g_parameterized_callbacks = {}
