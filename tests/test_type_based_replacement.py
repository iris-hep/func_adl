import ast
import copy
import logging
from typing import Any, Callable, Iterable, Optional, Tuple, Type, TypeVar, cast

import pytest

from func_adl import ObjectStream
from func_adl.type_based_replacement import (
    func_adl_callable,
    func_adl_callback,
    func_adl_parameterized_call,
    register_func_adl_os_collection,
    remap_by_types,
    remap_from_lambda,
)


class Track:
    def pt(self) -> float:
        ...

    def eta(self) -> float:
        ...


T = TypeVar("T")


def add_track_extra_info(s: ObjectStream[T], a: ast.Call) -> Tuple[ObjectStream[T], ast.Call]:
    s_update = s.MetaData({"t": "track stuff"})
    return s_update, a


@func_adl_callback(add_track_extra_info)
class TrackStuff:
    def pt(self) -> float:
        ...

    def eta(self) -> float:
        ...


class Jet:
    def pt(self) -> float:
        ...

    def eta(self) -> float:
        ...

    def tracks(self) -> Iterable[Track]:
        ...


def ast_lambda(lambda_func: str) -> ast.Lambda:
    "Return the ast starting from the Lambda node"
    return ast.parse(lambda_func).body[0].value  # type: ignore


def add_met_extra_info(s: ObjectStream[T], a: ast.Call) -> Tuple[ObjectStream[T], ast.Call]:
    s_update = s.MetaData({"j": "pxyz stuff"})
    return s_update, a


@func_adl_callback(add_met_extra_info)
class met_extra:
    def pxy(self) -> float:
        ...


def add_met_info(s: ObjectStream[T], a: ast.Call) -> Tuple[ObjectStream[T], ast.Call]:
    s_update = s.MetaData({"j": "pxy stuff"})
    return s_update, a


def add_met_method_info(s: ObjectStream[T], a: ast.Call) -> Tuple[ObjectStream[T], ast.Call]:
    s_update = s.MetaData({"j": "custom stuff"})
    return s_update, a


@func_adl_callback(add_met_info)
class met:
    def pxy(self) -> float:
        ...

    def isGood(self) -> bool:
        ...

    def metobj(self) -> met_extra:
        ...

    @func_adl_callback(add_met_method_info)
    def custom(self) -> float:
        ...


def add_collection(s: ObjectStream[T], a: ast.Call) -> Tuple[ObjectStream[T], ast.Call]:
    """Add a collection to the object stream"""
    assert isinstance(a.func, ast.Attribute)
    if a.func.attr == "Jets":
        s_update = s.MetaData({"j": "stuff"})
        return s_update, a
    elif a.func.attr == "EventNumber":
        new_call = copy.copy(a)
        new_call.args = [ast_lambda("20")]
        return s, new_call
    else:
        return s, a


class MyIterable(Iterable[T]):
    def Last(self) -> T:
        "Return the last element in the sequence"
        ...

    def Where(self, test: Callable[[T], bool]) -> Iterable[T]:
        ...


@func_adl_callback(add_collection)
class Event:
    def Jets(self, bank: str = "default") -> Iterable[Jet]:
        ...

    def JetsIterSub(self, bank: str = "default") -> MyIterable[Jet]:
        ...

    def Jets_req(self, bank_required: str) -> Iterable[Jet]:
        ...

    def MET(self) -> met:
        ...

    def MET_noreturntype(self):
        ...

    def Tracks(self) -> Iterable[Track]:
        ...

    def TrackStuffs(self) -> Iterable[TrackStuff]:
        ...

    def EventNumber(self) -> int:
        ...

    def MyLambdaCallback(self, cb: Callable) -> int:
        ...


def return_type_test(expr: str, arg_type: type, expected_type: type):
    s = ast_lambda(expr)
    objs = ObjectStream(ast.Name(id="e", ctx=ast.Load()), arg_type)

    _, _, expr_type = remap_by_types(objs, "e", arg_type, s)
    assert expr_type == expected_type


def test_int():
    return_type_test("1", int, int)


def test_int_neg():
    return_type_test("-11", int, int)


def test_bool():
    return_type_test("False", int, bool)


def test_str():
    return_type_test('"hi"', int, str)


def test_float():
    return_type_test("1.5", int, float)


def test_any():
    return_type_test("e", Any, Any)


def test_neg_float():
    return_type_test("-1.5", int, float)


def test_add_int():
    return_type_test("e+1", int, int)


def test_add_float():
    return_type_test("e+1.5", int, float)


def test_sub_int():
    return_type_test("e-1", int, int)


def test_sub_float():
    return_type_test("e-1.5", int, float)


def test_mul_int():
    return_type_test("e*1", int, int)


def test_mul_float():
    return_type_test("e*1.5", int, float)


def test_div_int():
    return_type_test("e/2", int, float)


def test_dib_float():
    return_type_test("e/1.5", int, float)


def test_bool_expression():
    "A bool expression"
    return_type_test("1 > 2", int, bool)


def test_bool_and_expression():
    "Using and"
    return_type_test("True and True", int, bool)


def test_bool_or_expression():
    "Using and"
    return_type_test("True or True", int, bool)


def test_abs_function_int_e():
    "A call to abs with an integer"
    return_type_test("abs(e)", int, float)


def test_abs_function_int_const():
    "A call to abs with an integer"
    return_type_test("abs(-23)", int, float)


def test_abs_function_float():
    "A call to abs with an float"
    return_type_test("abs(e)", float, float)


def test_ifexpr_onetype():
    "A ? expression"
    return_type_test("1 if True else 2", int, int)


def test_ifexpr_onetype_twotype_math():
    "A ? expression"
    return_type_test("1 if True else 2.2", int, float)


def test_ifexpr_onetype_twotypes():
    "A ? expression"
    with pytest.raises(ValueError) as e:
        return_type_test('1 if True else "2.2"', int, float)
    assert "str" in str(e)


def test_subscript():
    return_type_test("e[0]", Iterable[int], int)


def test_subscript_any():
    return_type_test("e[0]", Any, Any)


def test_collection():
    "A simple collection"
    s = ast_lambda("e.Jets('default')")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.Jets('default')"))
    assert ast.dump(new_objs.query_ast) == ast.dump(ast_lambda("MetaData(e, {'j': 'stuff'})"))
    assert expr_type == Iterable[Jet]


def test_required_arg():
    "A simple collection"
    s = ast_lambda("e.Jets_req()")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    with pytest.raises(ValueError) as e:
        remap_by_types(objs, "e", Event, s)

    assert "bank_required" in str(e)


def test_collection_with_default():
    "A simple collection"
    s = ast_lambda("e.Jets()")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.Jets('default')"))
    assert ast.dump(new_objs.query_ast) == ast.dump(ast_lambda("MetaData(e, {'j': 'stuff'})"))
    assert expr_type == Iterable[Jet]


def test_shortcut_nested_callback():
    """When there is a simple return, like Where, make sure that lambdas
    inside the method are called"""

    s = ast_lambda("e.TrackStuffs().Where(lambda t: abs(t.pt()) > 10)")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert ast.dump(new_s) == ast.dump(
        ast_lambda("e.TrackStuffs().Where(lambda t: abs(t.pt()) > 10)")
    )
    assert ast.dump(new_objs.query_ast) == ast.dump(
        ast_lambda("MetaData(e, {'t': 'track stuff'})")
    )
    assert expr_type == Iterable[TrackStuff]


def test_shortcut_2nested_callback():
    """When there is a simple return, like Where, make sure that lambdas
    inside the method are called, but double inside"""

    s = ast_lambda(
        "ds.Select(lambda e: e.TrackStuffs()).Select(lambda ts: ts.Where(lambda t: t.pt() > 10))"
    )
    objs = ObjectStream[Iterable[Event]](ast.Name(id="ds", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "ds", Iterable[Event], s)

    assert ast.dump(new_s) == ast.dump(
        ast_lambda(
            "ds.Select(lambda e: e.TrackStuffs())"
            ".Select(lambda ts: ts.Where(lambda t: t.pt() > 10))"
        )
    )
    assert ast.dump(new_objs.query_ast) == ast.dump(
        ast_lambda("MetaData(ds, {'t': 'track stuff'})")
    )
    assert expr_type == Iterable[Iterable[TrackStuff]]


def test_collection_First(caplog):
    "A simple collection"
    caplog.set_level(logging.WARNING)

    s = ast_lambda("e.Jets().First()")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    _, _, expr_type = remap_by_types(objs, "e", Event, s)

    assert expr_type == Jet

    assert len(caplog.text) == 0


def test_collection_Custom_Method_int(caplog):
    "A custom collection method not pre-given"
    caplog.set_level(logging.WARNING)

    M = TypeVar("M")

    @register_func_adl_os_collection
    class CustomCollection(ObjectStream[M]):
        def __init__(self, a: ast.AST, item_type: Optional[Type] = None):
            super().__init__(a, item_type)

        def MyFirst(self) -> int:
            ...

    s = ast_lambda("e.Jets().MyFirst()")
    objs = CustomCollection[Event](ast.Name(id="e", ctx=ast.Load()), Event)

    _, _, expr_type = remap_by_types(objs, "e", Event, s)

    assert expr_type == int

    assert len(caplog.text) == 0


def test_collection_Custom_Method_multiple_args(caplog):
    "A custom collection method not pre-given"
    caplog.set_level(logging.WARNING)

    M = TypeVar("M")

    @register_func_adl_os_collection
    class CustomCollection(ObjectStream[M]):
        def __init__(self, a: ast.AST, item_type=Any):
            super().__init__(a, item_type)

        def MyFirst(self, arg1: int, arg2: int) -> int:
            ...

    s = ast_lambda("e.Jets().MyFirst(1,3)")
    objs = CustomCollection[Event](ast.Name(id="e", ctx=ast.Load()))

    _, _, expr_type = remap_by_types(objs, "e", Event, s)

    assert expr_type == int

    assert len(caplog.text) == 0


def test_collection_Custom_Method_default(caplog):
    "A custom collection method not pre-given"
    caplog.set_level(logging.WARNING)

    M = TypeVar("M")

    @register_func_adl_os_collection
    class CustomCollection_default(ObjectStream[M]):
        def __init__(self, a: ast.AST, item_type):
            super().__init__(a, item_type)

        def Take(self, n: int = 5) -> ObjectStream[M]:
            ...

    s = ast_lambda("e.Jets().Take()")
    objs = CustomCollection_default[Event](ast.Name(id="e", ctx=ast.Load()), Event)

    _, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert expr_type == ObjectStream[Jet]
    assert ast.dump(new_s) == ast.dump(ast_lambda("e.Jets('default').Take(5)"))

    assert len(caplog.text) == 0


def test_collection_Custom_Method_Jet(caplog):
    "A custom collection method not pre-given"
    caplog.set_level(logging.WARNING)

    M = TypeVar("M")

    class CustomCollection_Jet(ObjectStream[M]):
        def __init__(self, a: ast.AST, item_type):
            super().__init__(a, item_type)

        def MyFirst(self) -> M:
            ...

    register_func_adl_os_collection(CustomCollection_Jet)

    s = ast_lambda("e.Jets().MyFirst()")
    objs = CustomCollection_Jet[Event](ast.Name(id="e", ctx=ast.Load()), Event)

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert expr_type == Jet

    assert len(caplog.text) == 0


def test_collection_CustomIterable(caplog):
    "A simple collection from an iterable with its own defined terminals"
    caplog.set_level(logging.WARNING)

    s = ast_lambda("e.JetsIterSub().Last()")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert expr_type == Jet

    assert len(caplog.text) == 0


def test_collection_CustomIterable_fallback(caplog):
    "A simple collection from an iterable with its own defined terminals"
    caplog.set_level(logging.WARNING)

    s = ast_lambda("e.JetsIterSub().Where(lambda j: j.pt() > 10)")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert expr_type == Iterable[Jet]

    assert len(caplog.text) == 0


def test_collection_lambda_not_followed(caplog):
    "Warn if a lambda is not tracked"
    caplog.set_level(logging.WARNING)

    s = ast_lambda("e.MyLambdaCallback(lambda f: True)")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert expr_type == int

    assert "lambda" in caplog.text.lower()
    assert "MyLambdaCallback" in caplog.text


def test_collection_Where(caplog):
    "A simple collection"
    caplog.set_level(logging.WARNING)

    s = ast_lambda("e.Jets().Where(lambda f: True)")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert expr_type == Iterable[Jet]

    assert len(caplog.text) == 0


def test_collection_Select(caplog):
    "A simple collection"
    caplog.set_level(logging.WARNING)

    s = ast_lambda("e.Jets().Select(lambda j: j.pt())")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert expr_type == Iterable[float]

    assert len(caplog.text) == 0


def test_collection_Select_meta(caplog):
    "A simple collection"
    caplog.set_level(logging.WARNING)

    s = ast_lambda("e.TrackStuffs().Select(lambda t: t.pt())")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert expr_type == Iterable[float]
    assert ast.dump(new_objs.query_ast) == ast.dump(
        ast_lambda("MetaData(e, {'t': 'track stuff'})")
    )

    assert len(caplog.text) == 0


def test_method_on_collection():
    "Call a method that requires some special stuff on a returend object"
    s = ast_lambda("e.MET().pxy()")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.MET().pxy()"))
    assert ast.dump(new_objs.query_ast) == ast.dump(ast_lambda("MetaData(e, {'j': 'pxy stuff'})"))
    assert expr_type == float


def test_method_callback():
    "Call a method that requires some special stuff on a returend object"
    s = ast_lambda("e.MET().custom()")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.MET().custom()"))
    assert ast.dump(new_objs.query_ast) == ast.dump(
        ast_lambda("MetaData(MetaData(e, {'j': 'pxy stuff'}), {'j': 'custom stuff'})")
    )
    assert expr_type == float


def test_method_on_collection_bool():
    "Call a method that requires some special stuff on a returend object"
    s = ast_lambda("e.MET().isGood()")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    _, _, expr_type = remap_by_types(objs, "e", Event, s)

    assert expr_type == bool


def test_method_on_method_on_collection():
    "Call a method that requires some special stuff on a returend object"
    s = ast_lambda("e.MET().metobj().pxy()")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()), Event)

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.MET().metobj().pxy()"))
    assert ast.dump(new_objs.query_ast) == ast.dump(
        ast_lambda("MetaData(MetaData(e, {'j': 'pxy stuff'}), {'j': 'pxyz stuff'})")
    )
    assert expr_type == float


def test_method_modify_ast():
    "Call a method that requires some special stuff on a returend object"
    s = ast_lambda("e.EventNumber()")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.EventNumber(20)"))
    assert ast.dump(new_objs.query_ast) == ast.dump(ast_lambda("e"))
    assert expr_type == int


def test_method_with_no_return_type(caplog):
    "A simple collection"
    caplog.set_level(logging.WARNING)
    s = ast_lambda("e.MET_noreturntype().pxy()")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.MET_noreturntype().pxy()"))
    assert ast.dump(new_objs.query_ast) == ast.dump(ast_lambda("e"))
    assert expr_type == Any
    assert "MET_noreturntype" in caplog.text


def test_method_with_no_prototype(caplog):
    "A simple collection"
    caplog.set_level(logging.WARNING)
    s = ast_lambda("e.MET_bogus().pxy()")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.MET_bogus().pxy()"))
    assert ast.dump(new_objs.query_ast) == ast.dump(ast_lambda("e"))
    assert expr_type == Any
    assert "MET_bogus" in caplog.text


def test_math_method(caplog):
    "A simple collection"
    caplog.set_level(logging.WARNING)
    s = ast_lambda("abs(e.MET.pxy())")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert len(caplog.text) == 0


def test_method_with_no_inital_type(caplog):
    "A simple collection"
    caplog.set_level(logging.WARNING)
    s = ast_lambda("e.MET_bogus().pxy()")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Any, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.MET_bogus().pxy()"))
    assert ast.dump(new_objs.query_ast) == ast.dump(ast_lambda("e"))
    assert expr_type == Any
    assert len(caplog.text) == 0


def test_bogus_method():
    "A method that is not typed"
    s = ast_lambda("e.Jetsss('default')")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.Jetsss('default')"))
    assert ast.dump(new_objs.query_ast) == ast.dump(ast_lambda("e"))
    assert expr_type == Any


def test_plain_object_method():
    "A method that is not typed"
    s = ast_lambda("j.pt()")
    objs = ObjectStream[Jet](ast.Name(id="j", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "j", Jet, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("j.pt()"))
    assert ast.dump(new_objs.query_ast) == ast.dump(ast_lambda("j"))
    assert expr_type == float


def test_function_with_processor():
    "Define a function we can use"

    def MySqrtProcessor(s: ObjectStream[T], a: ast.Call) -> Tuple[ObjectStream[T], ast.Call]:
        new_s = s.MetaData({"j": "func_stuff"})
        return new_s, a

    @func_adl_callable(MySqrtProcessor)
    def MySqrt(x: float) -> float:
        ...

    s = ast_lambda("MySqrt(2)")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()), item_type=Event)

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("MySqrt(2)"))
    assert ast.dump(new_objs.query_ast) == ast.dump(ast_lambda("MetaData(e, {'j': 'func_stuff'})"))
    assert new_objs.item_type == Event
    assert expr_type == float


def test_function_with_simple():
    "Define a function we can use"

    @func_adl_callable()
    def MySqrt(x: float) -> float:
        ...

    s = ast_lambda("MySqrt(2)")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("MySqrt(2)"))
    assert ast.dump(new_objs.query_ast) == ast.dump(ast_lambda("e"))
    assert expr_type == float


def test_function_with_missing_arg():
    "Define a function we can use"

    @func_adl_callable()
    def MySqrt(my_x: float) -> float:
        ...

    s = ast_lambda("MySqrt()")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    with pytest.raises(ValueError) as e:
        remap_by_types(objs, "e", Event, s)

    assert "my_x" in str(e)


def test_function_with_default():
    "Define a function we can use"

    @func_adl_callable()
    def MySqrt(x: float = 20) -> float:
        ...

    s = ast_lambda("MySqrt()")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("MySqrt(20)"))
    assert ast.dump(new_objs.query_ast) == ast.dump(ast_lambda("e"))
    assert expr_type == float


def test_function_with_default_inside():
    "A function with a default arg that is inside a select"

    @func_adl_callable()
    def MySqrt(x: float = 20) -> float:
        ...

    s = ast_lambda("e.Jets().Select(lambda j: MySqrt())")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert ast.dump(new_s) == ast.dump(
        ast_lambda("e.Jets('default').Select(lambda j: MySqrt(20))")
    )
    assert ast.dump(new_objs.query_ast) == ast.dump(ast_lambda("MetaData(e, {'j': 'stuff'})"))
    assert expr_type == Iterable[float]


def test_function_with_keyword():
    "Define a function we can use"

    @func_adl_callable()
    def MySqrt(x: float = 20) -> float:
        ...

    s = ast_lambda("MySqrt(x=15)")
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("MySqrt(15)"))
    assert ast.dump(new_objs.query_ast) == ast.dump(ast_lambda("e"))
    assert expr_type == float


def test_remap_lambda_helper():
    "Test simple usage of helper function"
    s = cast(ast.Lambda, ast_lambda("lambda e: e.Jets('default')"))
    objs = ObjectStream[Event](ast.Name(id="e", ctx=ast.Load()), item_type=Event)

    new_objs, new_s, rtn_type = remap_from_lambda(objs, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("lambda e: e.Jets('default')"))
    assert ast.dump(new_objs.query_ast) == ast.dump(ast_lambda("MetaData(e, {'j': 'stuff'})"))
    assert new_objs.item_type == Event
    assert rtn_type == Iterable[Jet]


def test_remap_lambda_subclass():
    "When objectstream is another class"

    class MyStream(ObjectStream[T]):
        def __init__(self, c, item_type: Type):
            super().__init__(c, item_type)

    s = cast(ast.Lambda, ast_lambda("lambda e: e.Jets('default')"))
    objs = MyStream[Event](ast.Name(id="e", ctx=ast.Load()), Event)

    new_objs, new_s, rtn_type = remap_from_lambda(objs, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("lambda e: e.Jets('default')"))
    assert ast.dump(new_objs.query_ast) == ast.dump(ast_lambda("MetaData(e, {'j': 'stuff'})"))
    assert rtn_type == Iterable[Jet]


def test_index_callback_1arg():
    "Indexed callback - make sure arg is passed correctly"

    param_1_capture = None

    def my_callback(
        s: ObjectStream[T], a: ast.Call, param_1: str
    ) -> Tuple[ObjectStream[T], ast.Call, Type]:
        nonlocal param_1_capture
        param_1_capture = param_1
        return (s.MetaData({"k": "stuff"}), a, float)

    class TEvent:
        @func_adl_parameterized_call(my_callback)
        @property
        def info(self):
            ...

    s = ast_lambda("e.info['fork'](55)")
    objs = ObjectStream[TEvent](ast.Name(id="e", ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, "e", TEvent, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.info(55)"))
    assert ast.dump(new_objs.query_ast) == ast.dump(ast_lambda("MetaData(e, {'k': 'stuff'})"))
    assert expr_type == float
    assert param_1_capture == "fork"


def test_index_callback_2arg():
    "Indexed callback - make sure 2 args are passed correctly"

    param_1_capture = None

    def my_callback(
        s: ObjectStream[T], a: ast.Call, param_1: str
    ) -> Tuple[ObjectStream[T], ast.Call, Type]:
        nonlocal param_1_capture
        param_1_capture = param_1
        return (s.MetaData({"k": "stuff"}), a, float)

    class TEvent:
        @func_adl_parameterized_call(my_callback)
        @property
        def info(self):
            ...

    s = ast_lambda("e.info['fork', 22](55)")
    objs = ObjectStream[TEvent](ast.Name(id="e", ctx=ast.Load()))

    remap_by_types(objs, "e", TEvent, s)

    assert param_1_capture == ("fork", 22)


def test_index_callback_modify_ast():
    "Indexed callback - make ast can be correctly modified"

    def my_callback(
        s: ObjectStream[T], a: ast.Call, param_1: str
    ) -> Tuple[ObjectStream[T], ast.Call, Type]:
        new_a = copy.copy(a)
        assert isinstance(a.func, ast.Attribute)
        new_a.func = ast.Attribute(value=a.func.value, attr="dude", ctx=a.func.ctx)

        return (s, new_a, float)

    class TEvent:
        @func_adl_parameterized_call(my_callback)
        @property
        def info(self):
            ...

    s = ast_lambda("e.info['fork'](55)")
    objs = ObjectStream[TEvent](ast.Name(id="e", ctx=ast.Load()))

    _, new_s, _ = remap_by_types(objs, "e", TEvent, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.dude(55)"))


def test_index_callback_modify_ast_nested():
    "Indexed callback - make ast can be correctly modified when nested in a Select"

    def my_callback(
        s: ObjectStream[T], a: ast.Call, param_1: str
    ) -> Tuple[ObjectStream[T], ast.Call, Type]:
        new_a = copy.copy(a)
        assert isinstance(a.func, ast.Attribute)
        new_a.func = ast.Attribute(value=a.func.value, attr="dude", ctx=a.func.ctx)

        return (s, new_a, float)

    class MyJet:
        @func_adl_parameterized_call(my_callback)
        @property
        def info(self):
            ...

    class TEvent:
        def Jets(self) -> Iterable[MyJet]:
            ...

    s = ast_lambda("e.Jets().Select(lambda j: j.info['fork'](55))")
    objs = ObjectStream[TEvent](ast.Name(id="e", ctx=ast.Load()))

    _, new_s, _ = remap_by_types(objs, "e", TEvent, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.Jets().Select(lambda j: j.dude(55))"))


def test_index_callback_on_method():
    "Add the decorator to the wrong type of thing."

    param_1_capture = None

    with pytest.raises(ValueError) as e:

        def my_callback(
            s: ObjectStream[T], a: ast.Call, param_1: str
        ) -> Tuple[ObjectStream[T], ast.Call, Type]:
            nonlocal param_1_capture
            param_1_capture = param_1
            return (s.MetaData({"k": "stuff"}), a, float)

        class TEvent:
            @func_adl_parameterized_call(my_callback)
            def info(self):
                ...

    assert "info" in str(e)


def test_index_callback_bad_prop():
    "Indexed callback - make sure arg is passed correctly"

    param_1_capture = None

    def my_callback(
        s: ObjectStream[T], a: ast.Call, param_1: str
    ) -> Tuple[ObjectStream[T], ast.Call, Type]:
        nonlocal param_1_capture
        param_1_capture = param_1
        return (s.MetaData({"k": "stuff"}), a, float)

    class TEvent:
        @func_adl_parameterized_call(my_callback)
        @property
        def info(self):
            ...

    s = ast_lambda("e.infoo['fork'](55)")
    objs = ObjectStream[TEvent](ast.Name(id="e", ctx=ast.Load()))
    with pytest.raises(AttributeError) as e:
        remap_by_types(objs, "e", TEvent, s)

    assert "infoo" in str(e)
    assert "TEvent" in str(e)


def test_index_callback_prop_not_dec():
    "Indexed callback - make sure arg is passed correctly"

    class TEvent:
        @property
        def info(self):
            ...

    s = ast_lambda("e.info['fork'](55)")
    objs = ObjectStream[TEvent](ast.Name(id="e", ctx=ast.Load()))
    with pytest.raises(ValueError) as e:
        remap_by_types(objs, "e", TEvent, s)

    assert "info" in str(e)
    assert "TEvent" in str(e)


def test_index_callback_prop_index_bad():
    "Indexed callback - make sure arg is passed correctly"

    class TEvent:
        @property
        def info(self):
            ...

    s = ast_lambda("e.info['fork':'dork'](55)")
    objs = ObjectStream[TEvent](ast.Name(id="e", ctx=ast.Load()))
    with pytest.raises(ValueError) as e:
        remap_by_types(objs, "e", TEvent, s)

    assert "info" in str(e)
    assert "TEvent" in str(e)
    assert "index" in str(e)
