# Test the object stream
import sys
from typing import Any, Optional
sys.path += ['.']
from func_adl import EventDataset
import ast
import asyncio
import pytest


class my_event(EventDataset):
    async def execute_result_async(self, a: ast.AST):
        await asyncio.sleep(0.01)
        return a

class MyTestException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

class my_event_boom(EventDataset):
    async def execute_result_async(self, a: ast.AST):
        await asyncio.sleep(0.01)
        raise MyTestException('this is a test bomb')

def test_simple_query():
    r = my_event() \
        .SelectMany("lambda e: e.jets()") \
        .Select("lambda j: j.pT()") \
        .AsROOTTTree("junk.root", "analysis", "jetPT") \
        .value()
    assert isinstance(r, ast.AST)


def test_simple_query_parquet():
    r = my_event() \
        .SelectMany("lambda e: e.jets()") \
        .Select("lambda j: j.pT()") \
        .AsParquetFiles("junk.root", 'jetPT') \
        .value()
    assert isinstance(r, ast.AST)


def test_simple_query_panda():
    r = my_event() \
        .SelectMany("lambda e: e.jets()") \
        .Select("lambda j: j.pT()") \
        .AsPandasDF(["analysis", "jetPT"]) \
        .value()
    assert isinstance(r, ast.AST)

def test_simple_query_awkward():
    r = my_event() \
        .SelectMany("lambda e: e.jets()") \
        .Select("lambda j: j.pT()") \
        .AsAwkwardArray(["analysis", "jetPT"]) \
        .value()
    assert isinstance(r, ast.AST)

def test_nested_query_rendered_correctly():
    r = my_event() \
        .Where("lambda e: e.jets.Select(lambda j: j.pT()).Where(lambda j: j > 10).Count() > 0") \
        .SelectMany("lambda e: e.jets()") \
        .AsROOTTTree("junk.root", "analysis", "jetPT") \
        .value()
    assert isinstance(r, ast.AST)
    assert "Select(source" not in ast.dump(r)

@pytest.mark.asyncio
async def test_await_exe_from_coroutine_with_throw():
    with pytest.raises(MyTestException):
        r = my_event_boom() \
            .SelectMany("lambda e: e.jets()") \
            .Select("lambda j: j.pT()") \
            .AsROOTTTree("junk.root", "analysis", "jetPT") \
            .value_async()
        await r

@pytest.mark.asyncio
async def test_await_exe_from_normal_function():
    r = my_event() \
        .SelectMany("lambda e: e.jets()") \
        .Select("lambda j: j.pT()") \
        .AsROOTTTree("junk.root", "analysis", "jetPT") \
        .value_async()
    assert isinstance(await r, ast.AST)


def test_ast_prop():
    r = my_event() \
        .SelectMany("lambda e: e.jets()") \
        .Select("lambda j: j.pT()") \
        .AsROOTTTree("junk.root", "analysis", "jetPT")

    assert isinstance(r.query_ast, ast.AST)
    assert isinstance(r.query_ast, ast.Call)



@pytest.mark.asyncio
async def test_2await_exe_from_coroutine():
    r1 = my_event() \
        .SelectMany("lambda e: e.jets()") \
        .Select("lambda j: j.pT()") \
        .AsROOTTTree("junk.root", "analysis", "jetPT") \
        .value_async()
    r2 = my_event() \
        .SelectMany("lambda e: e.jets()") \
        .Select("lambda j: j.eta()") \
        .AsROOTTTree("junk.root", "analysis", "jetPT") \
        .value_async()
    rpair = await asyncio.gather(r1, r2)
    assert isinstance(rpair[0], ast.AST)
    assert isinstance(rpair[1], ast.AST)


@pytest.mark.asyncio
async def test_passed_in_executor():
    logged_ast: Optional[ast.AST] = None
    
    async def my_exe(a: ast.AST) -> Any:
        nonlocal logged_ast
        logged_ast = a
        return 1
        
    r = my_event() \
        .SelectMany("lambda e: e.jets()") \
        .Select("lambda j: j.pT()") \
        .AsROOTTTree("junk.root", "analysis", "jetPT") \
        .value_async(executor=my_exe)

    assert (await r) == 1
    assert logged_ast is not None
