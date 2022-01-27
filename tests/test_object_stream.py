# Test the object stream
import ast
import asyncio
from func_adl.object_stream import ObjectStream
from typing import Any, Iterable, Optional, Tuple, TypeVar

import pytest
from func_adl import EventDataset


class my_event(EventDataset):
    async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
        await asyncio.sleep(0.01)
        return a


class my_event_with_title(EventDataset):
    async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
        await asyncio.sleep(0.01)
        return a, title


class dd_jet:
    def pt(self) -> float:
        ...

    def eta(self) -> float:
        ...


T = TypeVar('T')


def add_md_for_type(s: ObjectStream[T], a: ast.Call) -> Tuple[ObjectStream[T], ast.AST]:
    return s.MetaData({'hi': 'there'}), a


class dd_event:
    _func_adl_type_info = add_md_for_type

    def Jets(self, bank: str) -> Iterable[dd_jet]:
        ...


class my_event_with_type(EventDataset[dd_event]):
    def __init__(self):
        super().__init__(dd_event)

    async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
        await asyncio.sleep(0.01)
        return a


class MyTestException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


class my_event_boom(EventDataset):
    async def execute_result_async(self, a: ast.AST, title: Optional[str]):
        await asyncio.sleep(0.01)
        raise MyTestException('this is a test bomb')


def test_simple_query():
    r = my_event() \
        .SelectMany("lambda e: e.jets()") \
        .Select("lambda j: j.pT()") \
        .AsROOTTTree("junk.root", "analysis", "jetPT") \
        .value()
    assert isinstance(r, ast.AST)


def test_with_types():
    r = (my_event_with_type()
         .SelectMany(lambda e: e.Jets('jets'))
         .Select(lambda j: j.eta())
         .value())
    assert isinstance(r, ast.AST)
    assert 'there' in ast.dump(r)


def test_simple_quer_with_title():
    r = my_event_with_title() \
        .SelectMany("lambda e: e.jets()") \
        .Select("lambda j: j.pT()") \
        .AsROOTTTree("junk.root", "analysis", "jetPT") \
        .value(title='onetwothree')
    assert r[1] == 'onetwothree'


def test_simple_query_lambda():
    r = (my_event()
         .SelectMany(lambda e: e.jets())
         .Select(lambda j: j.pT())
         .AsROOTTTree("junk.root", "analysis", "jetPT")
         .value())
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


def test_metadata():
    r = my_event() \
        .MetaData({'one': 'two', 'two': 'three'}) \
        .SelectMany("lambda e: e.jets()") \
        .Select("lambda j: j.pT()") \
        .AsROOTTTree("junk.root", "analysis", "jetPT") \
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


def test_bad_where():
    with pytest.raises(ValueError):
        my_event() \
            .Where("lambda e: 10") \
            .SelectMany("lambda e: e.jets()") \
            .AsROOTTTree("junk.root", "analysis", "jetPT") \
            .value()


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

    async def my_exe(a: ast.AST, title: Optional[str]) -> Any:
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


def test_untyped():
    r = my_event()
    assert r.item_type == Any


def test_typed():
    class Jet:
        def pt(self) -> float:
            ...

    class Evt:
        def Jets(self) -> Iterable[Jet]:
            ...

    class evt_typed(EventDataset[Evt]):
        def __init__(self):
            super().__init__(Evt)

        async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
            await asyncio.sleep(0.01)
            return a

    r = evt_typed()
    assert r.item_type is Evt


def test_typed_with_select():
    class Jet:
        ...

    class Evt:
        def Jets(self) -> Iterable[Jet]:
            ...

    class evt_typed(EventDataset[Evt]):
        def __init__(self):
            super().__init__(Evt)

        async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
            await asyncio.sleep(0.01)
            return a

    r = (
            evt_typed()
            .Select(lambda e: e.Jets())
    )
    assert r.item_type is Iterable[Jet]


def test_typed_with_selectmany():
    class Jet:
        ...

    class Evt:
        def Jets(self) -> Iterable[Jet]:
            ...

    class evt_typed(EventDataset[Evt]):
        def __init__(self):
            super().__init__(Evt)

        async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
            await asyncio.sleep(0.01)
            return a

    r = (
            evt_typed()
            .SelectMany(lambda e: e.Jets())
    )
    assert r.item_type is Jet


def test_typed_with_select_and_selectmany():
    class Jet:
        def pt(self) -> float:
            ...

    class Evt:
        def Jets(self) -> Iterable[Jet]:
            ...

    class evt_typed(EventDataset[Evt]):
        def __init__(self):
            super().__init__(Evt)

        async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
            await asyncio.sleep(0.01)
            return a

        def Jets(self) -> Iterable[Jet]:
            ...

    r = (
            evt_typed()
            .SelectMany(lambda e: e.Jets())
            .Select(lambda j: j.pt())
    )
    assert r.item_type is float


def test_typed_with_where():
    class Evt:
        def MET(self) -> float:
            ...

    class evt_typed(EventDataset[Evt]):
        def __init__(self):
            super().__init__(Evt)

        async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
            await asyncio.sleep(0.01)
            return a

    r = (
            evt_typed()
            .Where(lambda e: e.MET() > 100)
    )
    assert r.item_type is Evt


def test_typed_with_metadata():
    class Evt:
        ...

    class evt_typed(EventDataset[Evt]):
        def __init__(self):
            super().__init__(Evt)

        async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
            await asyncio.sleep(0.01)
            return a

    r = (
            evt_typed()
            .MetaData({})
    )
    assert r.item_type is Evt
