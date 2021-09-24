import ast
from func_adl.type_based_replacement import remap_by_types
from typing import Iterable
from func_adl import ObjectStream


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


class met:
    def pxy(self) -> float:
        ...


class Event:
    __func_adl_annotations = {
        'Jets': {
            'metadata': {
                'j': 'stuff',
            }
        }
    }

    def Jets(self, bank: str = 'default') -> Iterable[Jet]:
        ...

    def MET(self, ) -> met:
        ...


def test_collection():
    'A simple collection'
    s = ast.parse("e.Jets()")
    objs = ObjectStream[Event](ast.Name(id='e'))

    new_objs, new_s = remap_by_types(objs, 'e', Event, s)

    assert ast.dump(new_s) == ast.parse("e.Jets('default')")
    assert ast.dump(new_objs.query_ast) == ast.parse("MetaData(e, {'j': 'stuff'}")


def test_method_on_collection():
    'A simple collection'
    s = ast.parse("e.MET().pxy()")
    objs = ObjectStream[Event](ast.Name(id='e'))

    new_objs, new_s = remap_by_types(objs, 'e', Event, s)

    assert ast.dump(new_s) == ast.parse("e.MET().pxy()/1000.0")
    assert ast.dump(new_objs.query_ast) == ast.parse("MetaData(e, {'j': 'pxy stuff'}")
