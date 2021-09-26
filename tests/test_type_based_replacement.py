import ast
from func_adl.type_based_replacement import remap_by_types
from typing import Iterable, Tuple, TypeVar
from func_adl import ObjectStream
import pytest


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


T = TypeVar('T')


def add_met_info(s: ObjectStream[T], a: ast.AST) -> Tuple[ObjectStream[T], ast.AST]:
    s_update = s.MetaData({'j': 'pxy stuff'})
    return s_update, a


class met:
    _func_adl_type_info = add_met_info

    def pxy(self) -> float:
        ...


def add_collection(s: ObjectStream[T], a: ast.Call) -> Tuple[ObjectStream[T], ast.AST]:
    '''Add a collection to the object stream
    '''
    assert isinstance(a.func, ast.Attribute)
    if a.func.attr == 'Jets':
        s_update = s.MetaData({'j': 'stuff'})
        return s_update, a
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


def test_collection():
    'A simple collection'
    s = ast.parse("e.Jets('default')")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()))

    new_objs, new_s = remap_by_types(objs, 'e', Event, s)

    assert ast.dump(new_s) == ast.dump(ast.parse("e.Jets('default')"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast.parse("MetaData(e, {'j': 'stuff'})").body[0].value)  # type: ignore


def test_required_arg():
    'A simple collection'
    s = ast.parse("e.Jets_req()")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()))

    with pytest.raises(ValueError) as e:
        remap_by_types(objs, 'e', Event, s)

    assert 'bank_required' in str(e)


def test_collection_with_default():
    'A simple collection'
    s = ast.parse("e.Jets()")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()))

    new_objs, new_s = remap_by_types(objs, 'e', Event, s)

    assert ast.dump(new_s) == ast.dump(ast.parse("e.Jets('default')"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast.parse("MetaData(e, {'j': 'stuff'})").body[0].value)  # type: ignore


def test_method_on_collection():
    'Call a method that requires some special stuff on a returend object'
    s = ast.parse("e.MET().pxy()")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()))

    new_objs, new_s = remap_by_types(objs, 'e', Event, s)

    assert ast.dump(new_s) == ast.dump(ast.parse("e.MET().pxy()"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast.parse("MetaData(e, {'j': 'pxy stuff'})").body[0].value)  # type: ignore


def test_method_with_no_return_type():
    'A simple collection'
    s = ast.parse("e.MET_noreturntype().pxy()")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()))

    new_objs, new_s = remap_by_types(objs, 'e', Event, s)

    assert ast.dump(new_s) == ast.dump(ast.parse("e.MET_noreturntype().pxy()"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast.parse("e").body[0].value)  # type: ignore


def test_bogus_method():
    'A method that is not typed'
    s = ast.parse("e.Jetsss('default')")
    objs = ObjectStream[Event](ast.Name(id='e', ctx=ast.Load()))

    new_objs, new_s = remap_by_types(objs, 'e', Event, s)

    assert ast.dump(new_s) == ast.dump(ast.parse("e.Jetsss('default')"))
    assert ast.dump(new_objs.query_ast) \
        == ast.dump(ast.parse("e").body[0].value)  # type: ignore