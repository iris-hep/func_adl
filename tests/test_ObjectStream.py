# Test the object stream
import sys
sys.path += ['.']
from func_adl import ObjectStream, ObjectStreamException, EventDatasetURLException, EventDataset
import ast
import asyncio
import pytest

def dummy_executor(a: ast.AST) -> ast.AST:
    'Called by the executor to run an AST'
    return a

async def dummy_executor_coroutine(a: ast.AST) -> ast.AST:
    'Called to evaluate a guy - but it will take a long time'
    await asyncio.sleep(0.01)
    return a

class MyTestException(BaseException):
    def __init__(self, msg):
        BaseException.__init__(self, msg)

async def dummy_executor_coroutine_with_throw(a: ast.AST) -> asyncio.Future:
    'Called to evaluate a guy - it will throw an exception to make sure it gets picked up.'
    await asyncio.sleep(0.01)
    raise MyTestException('this is a test bomb')

def test_simple_query():
    r = EventDataset("file://junk.root") \
        .SelectMany("lambda e: e.jets()") \
        .Select("lambda j: j.pT()") \
        .AsROOTTTree("junk.root", "analysis", "jetPT") \
        .value(dummy_executor)
    assert isinstance(r, ast.AST)

def test_simple_query_panda():
    r = EventDataset("file://junk.root") \
        .SelectMany("lambda e: e.jets()") \
        .Select("lambda j: j.pT()") \
        .AsPandasDF(["analysis", "jetPT"]) \
        .value(dummy_executor)
    assert isinstance(r, ast.AST)

def test_simple_query_awkward():
    r = EventDataset("file://junk.root") \
        .SelectMany("lambda e: e.jets()") \
        .Select("lambda j: j.pT()") \
        .AsAwkwardArray(["analysis", "jetPT"]) \
        .value(dummy_executor)
    assert isinstance(r, ast.AST)

def test_nested_query_rendered_correctly():
    r = EventDataset("file://junk.root") \
        .Where("lambda e: e.jets.Select(lambda j: j.pT()).Where(lambda j: j > 10).Count() > 0") \
        .SelectMany("lambda e: e.jets()") \
        .AsROOTTTree("junk.root", "analysis", "jetPT") \
        .value(dummy_executor)
    assert isinstance(r, ast.AST)
    assert "Select(source" not in ast.dump(r)

def test_executor_returns_a_coroutine():
    'When the executor returns a future, make sure it waits'
    r = EventDataset("file://junk.root") \
        .SelectMany("lambda e: e.jets()") \
        .Select("lambda j: j.pT()") \
        .AsROOTTTree("junk.root", "analysis", "jetPT") \
        .value(dummy_executor_coroutine)
    assert isinstance(r, ast.AST)

@pytest.mark.asyncio
async def test_await_exe_from_coroutine():
    r = EventDataset("file://junk.root") \
        .SelectMany("lambda e: e.jets()") \
        .Select("lambda j: j.pT()") \
        .AsROOTTTree("junk.root", "analysis", "jetPT") \
        .future_value(dummy_executor_coroutine)
    assert isinstance(await r, ast.AST)

@pytest.mark.asyncio
async def test_await_exe_from_coroutine_with_throw():
    saw_exception = False
    try:
        r = EventDataset("file://junk.root") \
            .SelectMany("lambda e: e.jets()") \
            .Select("lambda j: j.pT()") \
            .AsROOTTTree("junk.root", "analysis", "jetPT") \
            .future_value(dummy_executor_coroutine_with_throw)
        result = await r
        assert result is not None
    except MyTestException:
        saw_exception = True
    
    assert saw_exception

def test_await_exe_with_throw():
    saw_exception = False
    try:
        r = EventDataset("file://junk.root") \
            .SelectMany("lambda e: e.jets()") \
            .Select("lambda j: j.pT()") \
            .AsROOTTTree("junk.root", "analysis", "jetPT") \
            .value(dummy_executor_coroutine_with_throw)
        assert r is not None
    except MyTestException:
        saw_exception = True
    
    assert saw_exception

@pytest.mark.asyncio
async def test_fail_await():
    try:
        EventDataset("file://junk.root") \
            .SelectMany("lambda e: e.jets()") \
            .Select("lambda j: j.pT()") \
            .AsROOTTTree("junk.root", "analysis", "jetPT") \
            .value(dummy_executor_coroutine)
        assert False
    except ObjectStreamException:
        pass
@pytest.mark.asyncio
async def test_await_exe_from_normal_function():
    r = EventDataset("file://junk.root") \
        .SelectMany("lambda e: e.jets()") \
        .Select("lambda j: j.pT()") \
        .AsROOTTTree("junk.root", "analysis", "jetPT") \
        .future_value(dummy_executor)
    assert isinstance(await r, ast.AST)

@pytest.mark.asyncio
async def test_2await_exe_from_coroutine():
    r1 = EventDataset("file://junk.root") \
        .SelectMany("lambda e: e.jets()") \
        .Select("lambda j: j.pT()") \
        .AsROOTTTree("junk.root", "analysis", "jetPT") \
        .future_value(dummy_executor_coroutine)
    r2 = EventDataset("file://junk.root") \
        .SelectMany("lambda e: e.jets()") \
        .Select("lambda j: j.eta()") \
        .AsROOTTTree("junk.root", "analysis", "jetPT") \
        .future_value(dummy_executor_coroutine)
    rpair = await asyncio.gather(r1, r2)
    assert isinstance(rpair[0], ast.AST)
    assert isinstance(rpair[1], ast.AST)
