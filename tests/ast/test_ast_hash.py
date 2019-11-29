# Test various things about the hash functions we use for ast's.
import ast
from func_adl.ast import ast_hash
from func_adl import EventDataset
from asyncio import create_task

async def do_call (a):
    return a

def build_ast(ds_name:str) -> ast.AST:
    return EventDataset(ds_name) \
        .Select('lambda e: e.Jets("jets").SelectMany(lambda j: e.Tracks("InnerTracks")).First()') \
        .AsROOTTTree('dude.root', 'analysis', 'JetPt') \
        .value(executor=do_call)

def build_ast_array_1(ds_name:str) -> ast.AST:
    return EventDataset(ds_name) \
        .Select('lambda e: e.Jets("jets").SelectMany(lambda j: e.Tracks("InnerTracks")).First()') \
        .AsROOTTTree('dude.root', 'analysis', ['JetPt']) \
        .value(executor=do_call)

def build_ast_array_2(ds_name:str) -> ast.AST:
    return EventDataset(ds_name) \
        .Select('lambda e: e.Jets("jets").SelectMany(lambda j: e.Tracks("InnerTracks")).First()') \
        .AsROOTTTree('dude.root', 'analysis', ['JetPt', 'JetEta']) \
        .value(executor=do_call)

def test_ast_hash_works():
    a = build_ast("file://root.root")
    h = ast_hash.calc_ast_hash(a)
    assert h is not None

def test_ast_with_different_files_not_different():
    a1 = build_ast("file://root1.root")
    a2 = build_ast("file://root2.root")
    assert ast_hash.calc_ast_hash(a1) != ast_hash.calc_ast_hash(a2)

def test_slightly_different_queries():
    a1 = build_ast_array_1('file://root1.root')
    a2 = build_ast_array_2('file://root1.root')

    assert ast_hash.calc_ast_hash(a1) != ast_hash.calc_ast_hash(a2)
    