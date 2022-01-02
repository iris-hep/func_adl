from __future__ import annotations
import ast
import logging
from func_adl.type_based_replacement import func_adl_callable, remap_by_types, remap_from_lambda
from typing import Any, Iterable, Tuple, Type, TypeVar, cast
from func_adl import ObjectStream
import copy
import pytest

#
# NOTE: Keep the tests here the same as in the file `test_type_based_replacement_py310`.
# When 3.11 is the lowest version this file can be deleted.
# THis makes sure that delayed type-hint resolution will work properly!
#


class Track:
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
    'Return the ast starting from the Lambda node'
    return ast.parse(lambda_func).body[0].value  # type: ignore


T = TypeVar('T')


def add_met_extra_info(s: ObjectStream[T], a: ast.AST) -> Tuple[ObjectStream[T], ast.AST]:
    s_update = s.MetaData({'j': 'pxyz stuff'})
    return s_update, a


class met_extra:
    _func_adl_type_info = add_met_extra_info

    def pxy(self) -> float:
        ...


def add_met_info(s: ObjectStream[T], a: ast.AST) -> Tuple[ObjectStream[T], ast.AST]:
    s_update = s.MetaData({'j': 'pxy stuff'})
    return s_update, a


class met:
    _func_adl_type_info = add_met_info

    def pxy(self) -> float:
        ...

    def isGood(self) -> bool:
        ...

    def metobj(self) -> met_extra:
        ...


def add_collection(s: ObjectStream[T], a: ast.Call) -> Tuple[ObjectStream[T], ast.AST]:
    '''Add a collection to the object stream
    '''
    assert isinstance(a.func, ast.Attribute)
    if a.func.attr == 'Jets':
        s_update = s.MetaData({'j': 'stuff'})
        return s_update, a
    elif a.func.attr == 'EventNumber':
        new_call = copy.copy(a)
        new_call.args = [ast_lambda("20")]
        return s, new_call
    else:
        return s, a


class Event:
    _func_adl_type_info = add_collection

    def Jets(self, bank: str = 'default') -> Iterable[Jet]:
        ...

    def Jets_req(self, bank_required: str) -> Iterable[Jet]:
        ...

    def MET(self) -> met:
        ...

    def MET_noreturntype(self):
        ...

    def Tracks(self) -> Iterable[Track]:
        ...

    def EventNumber(self) -> int:
        ...


def return_type_test(expr: str, arg_type: type, expected_type: type):
    s = ast_lambda(expr)
    objs = ObjectStream(ast.Name(id='e', ctx=ast.Load()), arg_type)

    _, _, expr_type = remap_by_types(objs, 'e', arg_type, s)
    assert expr_type == expected_type


def test_int():
    return_type_test('1', int, int)


def test_int_neg():
    return_type_test('-11', int, int)


def test_bool():
    return_type_test('False', int, bool)


def test_str():
    return_type_test('"hi"', int, str)


def test_float():
    return_type_test('1.5', int, float)


def test_any():
    return_type_test('e', Any, Any)


def test_neg_float():
    return_type_test('-1.5', int, float)


def test_add_int():
    return_type_test('e+1', int, int)


def test_add_float():
    return_type_test('e+1.5', int, float)


def test_sub_int():
    return_type_test('e-1', int, int)


def test_sub_float():
    return_type_test('e-1.5', int, float)


def test_mul_int():
    return_type_test('e*1', int, int)


def test_mul_float():
    return_type_test('e*1.5', int, float)


def test_div_int():
    return_type_test('e/2', int, float)


def test_dib_float():
    return_type_test('e/1.5', int, float)


def test_bool_expression():
    'A bool expression'
    return_type_test('1 > 2', int, bool)


def test_abs_function_int_e():
    'A call to abs with an integer'
    return_type_test('abs(e)', int, float)


def test_abs_function_int_const():
    'A call to abs with an integer'
    return_type_test('abs(-23)', int, float)


def test_abs_function_float():
    'A call to abs with an float'
    return_type_test('abs(e)', float, float)


def test_ifexpr_onetype():
    'A ? expression'
    return_type_test('1 if True else 2', int, int)


def test_ifexpr_onetype_twotype_math():
    'A ? expression'
    return_type_test('1 if True else 2.2', int, float)


def test_ifexpr_onetype_twotypes():
    'A ? expression'
    with pytest.raises(ValueError) as e:
        return_type_test('1 if True else "2.2"', int, float)
    assert "str" in str(e)


def test_subscript():
    return_type_test('e[0]', Iterable[int], int)


def test_subscript_any():
    return_type_test('e[0]', Any, Any)


def test_collection():
    'A simple collection'
    s = ast_lambda("e.Jets('default')")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, 'e', Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.Jets('default')"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast_lambda("MetaData(e, {'j': 'stuff'})"))
    assert expr_type == Iterable[Jet]


def test_required_arg():
    'A simple collection'
    s = ast_lambda("e.Jets_req()")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()))

    with pytest.raises(ValueError) as e:
        remap_by_types(objs, 'e', Event, s)

    assert 'bank_required' in str(e)


def test_collection_with_default():
    'A simple collection'
    s = ast_lambda("e.Jets()")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, 'e', Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.Jets('default')"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast_lambda("MetaData(e, {'j': 'stuff'})"))
    assert expr_type == Iterable[Jet]


def test_method_on_collection():
    'Call a method that requires some special stuff on a returend object'
    s = ast_lambda("e.MET().pxy()")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, 'e', Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.MET().pxy()"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast_lambda("MetaData(e, {'j': 'pxy stuff'})"))
    assert expr_type == float


def test_method_on_collection_bool():
    'Call a method that requires some special stuff on a returend object'
    s = ast_lambda("e.MET().isGood()")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()))

    _, _, expr_type = remap_by_types(objs, 'e', Event, s)

    assert expr_type == bool


def test_method_on_method_on_collection():
    'Call a method that requires some special stuff on a returend object'
    s = ast_lambda("e.MET().metobj().pxy()")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()), Event)

    new_objs, new_s, expr_type = remap_by_types(objs, 'e', Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.MET().metobj().pxy()"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast_lambda("MetaData(MetaData(e, {'j': 'pxy stuff'}), {'j': 'pxyz stuff'})"))
    assert expr_type == float


def test_method_modify_ast():
    'Call a method that requires some special stuff on a returend object'
    s = ast_lambda("e.EventNumber()")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, 'e', Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.EventNumber(20)"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast_lambda("e"))
    assert expr_type == int


def test_method_with_no_return_type(caplog):
    'A simple collection'
    caplog.set_level(logging.WARNING)
    s = ast_lambda("e.MET_noreturntype().pxy()")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, 'e', Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.MET_noreturntype().pxy()"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast_lambda("e"))
    assert expr_type == Any
    assert "MET_noreturntype" in caplog.text


def test_method_with_no_prototype(caplog):
    'A simple collection'
    caplog.set_level(logging.WARNING)
    s = ast_lambda("e.MET_bogus().pxy()")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, 'e', Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.MET_bogus().pxy()"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast_lambda("e"))
    assert expr_type == Any
    assert "MET_bogus" in caplog.text


def test_method_with_no_inital_type(caplog):
    'A simple collection'
    caplog.set_level(logging.WARNING)
    s = ast_lambda("e.MET_bogus().pxy()")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, 'e', Any, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.MET_bogus().pxy()"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast_lambda("e"))
    assert expr_type == Any
    assert len(caplog.text) == 0


def test_bogus_method():
    'A method that is not typed'
    s = ast_lambda("e.Jetsss('default')")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, 'e', Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("e.Jetsss('default')"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast_lambda("e"))
    assert expr_type == Any


def test_plain_object_method():
    'A method that is not typed'
    s = ast_lambda("j.pt()")
    objs = ObjectStream[Jet](ast.Name(id='j', ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, 'j', Jet, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("j.pt()"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast_lambda("j"))
    assert expr_type == float


def test_function_with_processor():
    'Define a function we can use'
    def MySqrtProcessor(s: ObjectStream[T], a: ast.Call) -> Tuple[ObjectStream[T], ast.Call]:
        new_s = s.MetaData({'j': 'func_stuff'})
        return new_s, a

    @func_adl_callable(MySqrtProcessor)
    def MySqrt(x: float) -> float:
        ...

    s = ast_lambda("MySqrt(2)")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()), item_type=Event)

    new_objs, new_s, expr_type = remap_by_types(objs, 'e', Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("MySqrt(2)"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast_lambda("MetaData(e, {'j': 'func_stuff'})"))
    assert new_objs.item_type == Event
    assert expr_type == float


def test_function_with_simple():
    'Define a function we can use'
    @func_adl_callable()
    def MySqrt(x: float) -> float:
        ...

    s = ast_lambda("MySqrt(2)")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, 'e', Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("MySqrt(2)"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast_lambda("e"))
    assert expr_type == float


def test_function_with_missing_arg():
    'Define a function we can use'
    @func_adl_callable()
    def MySqrt(my_x: float) -> float:
        ...

    s = ast_lambda("MySqrt()")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()))

    with pytest.raises(ValueError) as e:
        remap_by_types(objs, 'e', Event, s)

    assert "my_x" in str(e)


def test_function_with_default():
    'Define a function we can use'
    @func_adl_callable()
    def MySqrt(x: float = 20) -> float:
        ...

    s = ast_lambda("MySqrt()")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, 'e', Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("MySqrt(20)"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast_lambda("e"))
    assert expr_type == float


def test_function_with_keyword():
    'Define a function we can use'
    @func_adl_callable()
    def MySqrt(x: float = 20) -> float:
        ...

    s = ast_lambda("MySqrt(x=15)")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()))

    new_objs, new_s, expr_type = remap_by_types(objs, 'e', Event, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda("MySqrt(15)"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast_lambda("e"))
    assert expr_type == float


def test_remap_lambda_helper():
    'Test simple usage of helper function'
    s = cast(ast.Lambda, ast_lambda("lambda e: e.Jets('default')"))
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()), item_type=Event)

    new_objs, new_s, rtn_type = remap_from_lambda(objs, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda(
        "lambda e: e.Jets('default')"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast_lambda("MetaData(e, {'j': 'stuff'})"))
    assert new_objs.item_type == Event
    assert rtn_type == Iterable[Jet]


def test_remap_lambda_subclass():
    'When objectstream is another class'

    class MyStream(ObjectStream[T]):
        def __init__(self, c, item_type: Type):
            super().__init__(c, item_type)

    s = cast(ast.Lambda, ast_lambda("lambda e: e.Jets('default')"))
    objs = MyStream[Event](ast.Name(id='e', ctx=ast.Load()), Event)

    new_objs, new_s, rtn_type = remap_from_lambda(objs, s)

    assert ast.dump(new_s) == ast.dump(ast_lambda(
        "lambda e: e.Jets('default')"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast_lambda("MetaData(e, {'j': 'stuff'})"))
    assert rtn_type == Iterable[Jet]