import inspect
import sys
import typing
from typing import Any, Dict, Optional, Tuple, Type, TypeVar

if sys.version_info >= (3, 8):
    from typing import get_args, get_origin
else:  # pragma: no cover
    # TODO: Remove this when we drop support for 3.7
    def get_args(tp):
        "Return arguments - this is done very simply and will fail ugly"
        return getattr(tp, "__args__", ())

    def get_origin(tp):
        "Return the origin - this is done very simply and will fail ugly"
        return getattr(tp, "__origin__", None)


def is_iterable(t: Type) -> bool:
    "Is this type iterable?"
    while (t is not Any) and (not _is_iterable_direct(t)):
        t = get_inherited(t)

    return t is not Any


def _is_iterable_direct(t: Type) -> bool:
    "Is this type iterable?"
    return getattr(t, "_name", None) == "Iterable" or getattr(t, "__name__", None) == "Iterable"


def get_inherited(t: Type) -> Type:
    """Returns the inherited type of `t`

    Notes:
    * This works for 3.7 forward (but not back!)

    Args:
        t (Type): The type (a class) that we should look at

    Returns:
        Type: The type for an inherited class, or `Any` if none can be found
    """
    if hasattr(t, "__orig_bases__"):
        base_classes = getattr(t, "__orig_bases__", None)
    elif hasattr(t, "__origin__") and hasattr(t.__origin__, "__orig_bases__"):
        base_classes = t.__origin__.__orig_bases__
    else:
        return Any

    r = base_classes[0]  # type: ignore

    g_args = get_args(t)
    if len(g_args) > 0:
        mapping = {a.__name__: v for a, v in zip(r.__parameters__, g_args)}

        r_base = get_origin(r)
        assert r_base is not None, "Internal error"

        # Get us back to typing if this is a common interface.
        # This is not needed in python 3.11 and forward, where
        # collections.abc.X can are all be parameterized.
        if r_base.__name__ in typing.__dict__:
            r_base = typing.__dict__[r_base.__name__]

        # Re-parameterize the type with the information e have from this parameterization.
        r = r_base[tuple(_resolve_type(t_arg, mapping) for t_arg in get_args(r))]

    return r


def unwrap_iterable(t: Type) -> Type:
    "Unwrap an iterable type"
    # Try to find an iterable in the history somehow

    while (t is not Any) and (not _is_iterable_direct(t)):
        t = get_inherited(t)

    if t == Any:
        return Any

    a = get_args(t)
    assert len(a) == 1, f"Coding error - expected iterable type with a parameter, got {t}"
    return a[0]


def build_type_dict_from_type(t: Type, at_class: Optional[Type] = None) -> Dict[str, TypeVar]:
    """Build a dictionary of type variables from a type

    Args:
        t (Type): The type to build the dictionary from
        at_type (Type): If there is some inheritance, then drop down to this level.
                        if we can't find it, then fail badly.

    Returns:
        Dict[str, Type]: The dictionary of type variables
    """
    d = {}
    generic_type = get_origin(t)
    if generic_type is None:
        if at_class is not None:
            raise TypeError(f"Could not find type {str(at_class)} in {str(t)}")
        return {}

    if at_class is not None and generic_type is not at_class:
        try:
            return build_type_dict_from_type(get_inherited(t), at_class)
        except TypeError as e:
            raise TypeError(f"Looked for generic parameters in {str(t)}") from e

    for a in zip(generic_type.__parameters__, get_args(t)):
        d[a[0].__name__] = a[1]
    return d


def _resolve_type(t: Type, parameters: Dict[str, Type]) -> Optional[Type]:
    """Resolve any parameters in `t` with what we find in `parameters`

    int, {} => int
    ~T, {~T: int} => int
    ~K, {~T: int} => None

    Args:
        t (Type): The type to resolve
        parameters (Dict[str, Type]): The dict of types to resolve

    Returns:
        None if `t` is parameterized by unknown type var's
        The resolved type (a copy leaving `t` untouched) if TypeVar's are filled in
        The type if no substitution is required.
    """
    if isinstance(t, TypeVar):
        if t.__name__ in parameters:
            return parameters[t.__name__]
        return None

    template_params = getattr(t, "__parameters__", None)
    if template_params is not None and (len(template_params) > 0):
        resolved_params = [_resolve_type(p, parameters) for p in template_params]
        if None in resolved_params:
            return None
        return t[tuple(resolved_params)]

    # Non-parameterized types are easy
    return t


def resolve_type_vars(
    parameterized_type: Type, context_type: Type, at_class: Optional[Type] = None
) -> Optional[Type]:
    """Given an object definition in context_type, return a a resolved set of types based
    on parameterized type. If `parameterized_type` references unknown `TypeVars`, then return
    `None`.

    int, <any> -> int
    ~T, Iterable[T=int] -> int
    ~S, Iterable[T=int] -> None

    Args:
        parameterized_type (Type): The type whose parameters are to be resolved
        context_type (Type): The context to use to do the resolution
        at_class (Type): Where the resolution should happen

    Returns:
        Optional[Type]: [description]
    """
    try:
        s = build_type_dict_from_type(context_type, at_class)
    except TypeError:
        s = {}
    return _resolve_type(parameterized_type, s)


def get_class_name(t: Type) -> str:
    "Return a name of a class (parameterized if this is a generic)"
    n = getattr(t, "_name", None)
    if n is not None:
        return f'{n}[{",".join(get_class_name(a) for a in t.__args__)}]'

    n = getattr(t, "__name__", None)
    if n is not None:
        return n

    # bail because we don't know how to do it nicely here.
    return str(t)


def get_method_and_class(class_object: Type, method_name: str) -> Optional[Tuple[Type, Any]]:
    """Finds a method in the inheritance hierarchy of a class object, and returns the
    class object where the method is defined, and the method object. If there is no such
    method it returns None.

    Args:
        class_object (Type): The class object to start the method search
        method_name (str): Name of the method to search for

    Returns:
        Optional[Tuple[Type, Any]]: None if the method can't be found
            Type: The class object where the method is defined
            Any: The method object
    """
    # Safely handle crazy requests
    if class_object is Any:
        return None

    # Check for templated classes
    # TODO: Use inspect.getmro
    if not hasattr(class_object, "__mro__"):
        class_object = get_origin(class_object)

    # Walk the resolution hierarchy to find the method
    found_obj = None
    found_method = None
    for c in inspect.getmro(class_object):
        m = getattr(c, method_name, None)
        if found_method is None and m is None:
            # We can't find the method!
            return None
        if found_method is None:
            found_obj = c
            found_method = m
        else:
            if found_method == m:
                found_obj = c
            else:
                return (found_obj, found_method)

    return (found_obj, found_method)
