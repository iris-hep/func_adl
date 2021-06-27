# Test various things about the hash functions we use for ast's.
import ast
from typing import Optional
from func_adl.ast import ast_hash
from func_adl import EventDataset


class my_event(EventDataset):
    async def execute_result_async(self, a: ast.AST, title: Optional[str]):
        return a


def build_ast() -> ast.AST:
    return my_event() \
        .Select('lambda e: e.Jets("jets").SelectMany(lambda j: e.Tracks("InnerTracks")).First()') \
        .AsROOTTTree('dude.root', 'analysis', 'JetPt') \
        .value()


def build_ast_array_1() -> ast.AST:
    return my_event() \
        .Select('lambda e: e.Jets("jets").SelectMany(lambda j: e.Tracks("InnerTracks")).First()') \
        .AsROOTTTree('dude.root', 'analysis', ['JetPt']) \
        .value()


def build_ast_array_2() -> ast.AST:
    return my_event() \
        .Select('lambda e: e.Jets("jets").SelectMany(lambda j: e.Tracks("InnerTracks")).First()') \
        .AsROOTTTree('dude.root', 'analysis', ['JetPt', 'JetEta']) \
        .value()


def test_ast_hash_works():
    a = build_ast()
    h = ast_hash.calc_ast_hash(a)
    assert h is not None


def test_slightly_different_queries():
    a1 = build_ast_array_1()
    a2 = build_ast_array_2()

    assert ast_hash.calc_ast_hash(a1) != ast_hash.calc_ast_hash(a2)
