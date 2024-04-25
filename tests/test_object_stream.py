# Test the object stream
import ast
import asyncio
import logging
from _ast import Call
from enum import Enum
from typing import Any, Iterable, Optional, Tuple, TypeVar

import pytest

from func_adl import EventDataset
from func_adl.object_stream import ObjectStream
from func_adl.type_based_replacement import func_adl_callback


class my_event(EventDataset):
    async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
        await asyncio.sleep(0.01)
        return a


class my_event_with_title(EventDataset):
    async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
        await asyncio.sleep(0.01)
        return a, title


class dd_jet:
    def pt(self) -> float: ...  # noqa

    def eta(self) -> float: ...  # noqa


T = TypeVar("T")


def add_md_for_type(s: ObjectStream[T], a: ast.Call) -> Tuple[ObjectStream[T], ast.Call]:
    return s.MetaData({"hi": "there"}), a


@func_adl_callback(add_md_for_type)
class dd_event:
    def Jets(self, bank: str) -> Iterable[dd_jet]: ...  # noqa


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
        raise MyTestException("this is a test bomb")


def test_simple_query():
    r = (
        my_event()
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .AsROOTTTree("junk.root", "analysis", "jetPT")
        .value()
    )
    assert isinstance(r, ast.AST)


def test_simple_query_one_line():
    """Make sure we parse 2 functions on one line correctly"""
    r = my_event().Select(lambda e: e.met).Where(lambda e: e > 10).value()
    assert isinstance(r, ast.AST)


def test_two_simple_query():
    r1 = (
        my_event()
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .AsROOTTTree("junk.root", "analysis", "jetPT")
        .value()
    )
    r2 = (
        my_event()
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .AsROOTTTree("junk.root", "analysis", ["jetPT"])
        .value()
    )

    assert ast.dump(r1) == ast.dump(r2)


def test_query_bad_variable():
    class my_type:
        def __init__(self, n):
            self._n = 10

    my_10 = my_type(10)

    with pytest.raises(ValueError) as e:
        (
            my_event()
            .SelectMany(lambda e: e.jets())
            .Select(lambda j: j.pT() > my_10)
            .AsROOTTTree("junk.root", "analysis", "jetPT")
            .value()
        )

    assert "my_type" in str(e)


def test_with_types():
    r1 = my_event_with_type().SelectMany(lambda e: e.Jets("jets"))
    r = r1.Select(lambda j: j.eta()).value()
    assert isinstance(r, ast.AST)
    assert "there" in ast.dump(r)


def test_simple_quer_with_title():
    r = (
        my_event_with_title()
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .AsROOTTTree("junk.root", "analysis", "jetPT")
        .value(title="onetwothree")
    )
    assert r[1] == "onetwothree"


def test_simple_query_lambda():
    r = (
        my_event()
        .SelectMany(lambda e: e.jets())
        .Select(lambda j: j.pT())
        .AsROOTTTree("junk.root", "analysis", "jetPT")
        .value()
    )
    assert isinstance(r, ast.AST)


def test_simple_query_parquet():
    r = (
        my_event()
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .AsParquetFiles("junk.root", "jetPT")
        .value()
    )
    assert isinstance(r, ast.AST)


def test_two_simple_query_parquet():
    r1 = (
        my_event()
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .AsParquetFiles("junk.root", "jetPT")
        .value()
    )
    r2 = (
        my_event()
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .AsParquetFiles("junk.root", ["jetPT"])
        .value()
    )

    assert ast.dump(r1) == ast.dump(r2)


def test_simple_query_panda():
    r = (
        my_event()
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .AsPandasDF(["analysis", "jetPT"])
        .value()
    )
    assert isinstance(r, ast.AST)


def test_two_imple_query_panda():
    r1 = (
        my_event()
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .AsPandasDF(["analysis"])
        .value()
    )
    r2 = (
        my_event()
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .AsPandasDF(["analysis"])
        .value()
    )
    assert ast.dump(r1) == ast.dump(r2)


def test_simple_query_awkward():
    r = (
        my_event()
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .AsAwkwardArray(["analysis", "jetPT"])
        .value()
    )
    assert isinstance(r, ast.AST)


def test_simple_query_as_awkward():
    r = (
        my_event()
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .as_awkward(["analysis", "jetPT"])
        .value()
    )
    assert isinstance(r, ast.AST)


def test_two_similar_query_awkward():
    r1 = (
        my_event()
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .AsAwkwardArray(["analysis"])
        .value()
    )
    r2 = (
        my_event()
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .AsAwkwardArray("analysis")
        .value()
    )

    assert ast.dump(r1) == ast.dump(r2)


def test_metadata():
    r = (
        my_event()
        .MetaData({"one": "two", "two": "three"})
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .value()
    )
    assert isinstance(r, ast.AST)


def test_query_metadata():
    r = (
        my_event()
        .QMetaData({"one": "two", "two": "three"})
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .value()
    )
    assert isinstance(r, ast.AST)
    assert "MetaData" not in ast.dump(r)


def test_query_metadata_dup(caplog):
    r = (
        my_event()
        .QMetaData({"one": "two", "two": "three"})
        .QMetaData({"one": "two", "two": "three"})
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .value()
    )
    assert isinstance(r, ast.AST)
    assert len(caplog.text) == 0


def test_query_metadata_dup_update(caplog):
    caplog.set_level(logging.INFO)
    r = (
        my_event()
        .QMetaData({"one": "two", "two": "three"})
        .QMetaData({"one": "twoo", "two": "three"})
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .AsROOTTTree("junk.root", "analysis", "jetPT")
        .value()
    )
    assert isinstance(r, ast.AST)
    assert "one" in caplog.text
    assert "twoo" in caplog.text
    assert "two" in caplog.text


def test_query_metadata_composable(caplog):
    caplog.set_level(logging.INFO)
    r_base = my_event().QMetaData({"one": "1"})

    # Each of these is a different base and should not interfear.
    r1 = r_base.QMetaData({"two": "2"})
    r2 = r_base.QMetaData({"two": "2+"})

    from func_adl.ast.meta_data import lookup_query_metadata

    assert lookup_query_metadata(r1, "two") == "2"
    assert lookup_query_metadata(r2, "two") == "2+"

    assert len(caplog.text) == 0


def test_query_metadata_not_empty():
    r_base = my_event().QMetaData({"one": "1"})
    q_ast = r_base.query_ast

    class MDScanner(ast.NodeVisitor):
        def visit_Call(self, node: Call) -> Any:
            if not isinstance(node.func, ast.Name):
                return self.generic_visit(node)
            if node.func.id != "MetaData":
                return self.generic_visit(node)
            assert len(node.args) == 2
            md_dict = node.args[1]
            assert isinstance(md_dict, ast.Dict)
            assert len(md_dict.keys) > 0
            return self.generic_visit(node)

    MDScanner().visit(q_ast)


def test_nested_query_rendered_correctly():
    r = (
        my_event()
        .Where("lambda e: e.jets.Select(lambda j: j.pT()).Where(lambda j: j > 10).Count() > 0")
        .SelectMany("lambda e: e.jets()")
        .AsROOTTTree("junk.root", "analysis", "jetPT")
        .value()
    )
    assert isinstance(r, ast.AST)
    assert "Select(source" not in ast.dump(r)


def test_query_with_comprehensions():
    r = (
        my_event()
        .Where("lambda e: [j.pT()>10 for j in e.jets].Count() > 0")
        .SelectMany("lambda e: e.jets()")
        .AsROOTTTree("junk.root", "analysis", "jetPT")
        .value()
    )
    assert isinstance(r, ast.AST)
    assert "ListComp" not in ast.dump(r)


def test_non_imported_function_call():
    r = (
        my_event()
        .Select(lambda event: np.cos(event.MET_phi))  # type: ignore # noqa
        .Where(lambda p: p > 0.0)
        .value()
    )  # NOQA
    assert isinstance(r, ast.AST)
    assert "Attribute(value=Name(id='np', ctx=Load()), attr='cos', ctx=Load())" in ast.dump(r)


def test_imported_function_call():
    import numpy as np

    r = my_event().Select(lambda event: np.cos(event.MET_phi)).Where(lambda p: p > 0.0).value()
    assert isinstance(r, ast.AST)
    assert "Attribute(value=Name(id='np', ctx=Load()), attr='cos', ctx=Load())" in ast.dump(r)


def test_bad_where():
    with pytest.raises(ValueError):
        my_event().Where("lambda e: 10").SelectMany("lambda e: e.jets()").AsROOTTTree(
            "junk.root", "analysis", "jetPT"
        ).value()


@pytest.mark.asyncio
async def test_await_exe_from_coroutine_with_throw():
    with pytest.raises(MyTestException):
        r = (
            my_event_boom()
            .SelectMany("lambda e: e.jets()")
            .Select("lambda j: j.pT()")
            .AsROOTTTree("junk.root", "analysis", "jetPT")
            .value_async()
        )
        await r


@pytest.mark.asyncio
async def test_await_exe_from_normal_function():
    r = (
        my_event()
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .AsROOTTTree("junk.root", "analysis", "jetPT")
        .value_async()
    )
    assert isinstance(await r, ast.AST)


def test_ast_prop():
    r = (
        my_event()
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .AsROOTTTree("junk.root", "analysis", "jetPT")
    )

    assert isinstance(r.query_ast, ast.AST)
    assert isinstance(r.query_ast, ast.Call)


@pytest.mark.asyncio
async def test_2await_exe_from_coroutine():
    r1 = (
        my_event()
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .AsROOTTTree("junk.root", "analysis", "jetPT")
        .value_async()
    )
    r2 = (
        my_event()
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.eta()")
        .AsROOTTTree("junk.root", "analysis", "jetPT")
        .value_async()
    )
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

    r = (
        my_event()
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .AsROOTTTree("junk.root", "analysis", "jetPT")
        .value_async(executor=my_exe)
    )

    assert (await r) == 1
    assert logged_ast is not None


def test_untyped():
    r = my_event()
    assert r.item_type == Any


def test_typed():
    class Jet:
        def pt(self) -> float: ...  # noqa

    class Evt:
        def Jets(self) -> Iterable[Jet]: ...  # noqa

    class evt_typed(EventDataset[Evt]):
        def __init__(self):
            super().__init__(Evt)

        async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
            await asyncio.sleep(0.01)
            return a

    r = evt_typed()
    assert r.item_type is Evt


def test_typed_with_select():
    class Jet: ...  # noqa

    class Evt:
        def Jets(self) -> Iterable[Jet]: ...  # noqa

    class evt_typed(EventDataset[Evt]):
        def __init__(self):
            super().__init__(Evt)

        async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
            await asyncio.sleep(0.01)
            return a

    r = evt_typed().Select(lambda e: e.Jets())
    assert r.item_type is Iterable[Jet]


def test_typed_with_selectmany():
    class Jet: ...  # noqa

    class Evt:
        def Jets(self) -> Iterable[Jet]: ...  # noqa

    class evt_typed(EventDataset[Evt]):
        def __init__(self):
            super().__init__(Evt)

        async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
            await asyncio.sleep(0.01)
            return a

    r = evt_typed().SelectMany(lambda e: e.Jets())
    assert r.item_type is Jet


def test_typed_with_select_and_selectmany():
    class Jet:
        def pt(self) -> float: ...  # noqa

    class Evt:
        def Jets(self) -> Iterable[Jet]: ...  # noqa

    class evt_typed(EventDataset[Evt]):
        def __init__(self):
            super().__init__(Evt)

        async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
            await asyncio.sleep(0.01)
            return a

        def Jets(self) -> Iterable[Jet]: ...  # noqa

    r1 = evt_typed().SelectMany(lambda e: e.Jets())
    r = r1.Select(lambda j: j.pt())
    assert r.item_type is float


def test_typed_with_where():
    class Evt:
        def MET(self) -> float: ...  # noqa

    class evt_typed(EventDataset[Evt]):
        def __init__(self):
            super().__init__(Evt)

        async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
            await asyncio.sleep(0.01)
            return a

    r = evt_typed().Where(lambda e: e.MET() > 100)
    assert r.item_type is Evt


def test_typed_with_metadata():
    class Evt: ...  # noqa

    class evt_typed(EventDataset[Evt]):
        def __init__(self):
            super().__init__(Evt)

        async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
            await asyncio.sleep(0.01)
            return a

    r = evt_typed().MetaData({})
    assert r.item_type is Evt


def test_typed_with_enum():
    class Evt:
        class Color(Enum):
            red = 1
            green = 2
            blue = 3

        def color(self) -> Color: ...  # noqa

    class evt_typed(EventDataset[Evt]):
        def __init__(self):
            super().__init__(Evt)

        async def execute_result_async(self, a: ast.AST, title: Optional[str] = None):
            await asyncio.sleep(0.01)
            return a

    r = evt_typed().Select(lambda e: e.color())
    assert r.item_type is Evt.Color
