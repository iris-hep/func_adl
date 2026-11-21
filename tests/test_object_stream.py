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


@pytest.mark.parametrize("operation", ["Skip", "Take"])
@pytest.mark.parametrize("count", [-1, 0, 2])
def test_slice_stream(operation, count):
    source = my_event_with_type()
    result = getattr(source, operation)(count)
    assert isinstance(result, my_event_with_type)
    assert result is not source
    assert result.item_type is dd_event
    assert isinstance(result.query_ast, ast.Call)
    assert result.query_ast.func.id == operation
    assert result.query_ast.args[0] is source.query_ast
    assert ast.literal_eval(result.query_ast.args[1]) == count


class MyTestException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


class my_event_boom(EventDataset):
    async def execute_result_async(self, a: ast.AST, title: Optional[str]):
        await asyncio.sleep(0.01)
        raise MyTestException("this is a test bomb")


def test_simple_query():
    r = my_event().SelectMany("lambda e: e.jets()").Select("lambda j: j.pT()").query_ast
    assert isinstance(r, ast.AST)


@pytest.mark.parametrize(
    "expression, expected",
    [
        (
            "j.index() in {i * 2 for i in [1, 2, 3]}",
            "j.index() == 2 or j.index() == 4 or j.index() == 6",
        ),
        ("j.index() not in {2 * 3, 8}", "j.index() != 6 and j.index() != 8"),
        ("j.index() in {i for i in []}", "False"),
    ],
)
def test_set_membership_prepared_for_executor(expression, expected):
    result = my_event().Where(f"lambda j: {expression}").clean_ast()
    expected_ast = ast.parse(f"Where(EventDataset(), lambda j: {expected})").body[0].value
    assert ast.dump(result) == ast.dump(expected_ast)
    assert not any(isinstance(n, (ast.Set, ast.SetComp, ast.BinOp)) for n in ast.walk(result))


@pytest.mark.parametrize("expression", ["{i for i in [1, 2]}", "set()", "{1, 2}"])
def test_standalone_set_rejected_during_query_construction(expression):
    with pytest.raises(ValueError, match="Set values are only supported") as error:
        my_event().Select(f"lambda e: {expression}")
    assert expression in str(error.value)


def test_simple_query_one_line():
    """Make sure we parse 2 functions on one line correctly"""
    r = my_event().Select(lambda e: e.met).Where(lambda e: e > 10).query_ast
    assert isinstance(r, ast.AST)


def test_two_simple_query():
    r1 = my_event().SelectMany("lambda e: e.jets()").Select("lambda j: j.pT()").query_ast
    r2 = my_event().SelectMany("lambda e: e.jets()").Select("lambda j: j.pT()").query_ast

    assert ast.dump(r1) == ast.dump(r2)


def test_query_bad_variable():
    class my_type:
        def __init__(self, n):
            self._n = 10

    my_10 = my_type(10)

    with pytest.raises(ValueError) as e:
        (my_event().SelectMany(lambda e: e.jets()).Select(lambda j: j.pT() > my_10).query_ast)

    assert "my_type" in str(e)


def test_with_types():
    r1 = my_event_with_type().SelectMany(lambda e: e.Jets("jets"))
    r = r1.Select(lambda j: j.eta()).query_ast
    assert isinstance(r, ast.AST)
    assert "there" in ast.dump(r)


def test_simple_query_lambda():
    r = my_event().SelectMany(lambda e: e.jets()).Select(lambda j: j.pT()).query_ast
    assert isinstance(r, ast.AST)


def test_order_by_normalizes_ast():
    r = my_event().Select(lambda e: e).OrderBy(lambda e: e.pT()).query_ast
    expected = ast.parse("OrderBy(Select(EventDataset(), lambda e: e), lambda e: e.pT())")
    assert ast.dump(r) == ast.dump(expected.body[0].value)


def test_order_by_descending_normalizes_ast():
    r = my_event().Select(lambda e: e).OrderByDescending(lambda e: e.pT()).query_ast
    expected = ast.parse(
        "OrderByDescending(Select(EventDataset(), lambda e: e), lambda e: e.pT())"
    )
    assert ast.dump(r) == ast.dump(expected.body[0].value)


def test_order_by_composes_with_where_and_select():
    r = (
        my_event()
        .Where(lambda e: e.met > 10)
        .OrderBy(lambda e: e.met)
        .Select(lambda e: e)
        .query_ast
    )
    expected = ast.parse(
        "Select(OrderBy(Where(EventDataset(), lambda e: e.met > 10), lambda e: e.met), "
        "lambda e: e)"
    )
    assert ast.dump(r) == ast.dump(expected.body[0].value)


def test_order_by_preserves_key_selector_lambda():
    r = my_event().OrderBy(lambda e: e.jets().Count()).query_ast
    expected = ast.parse("OrderBy(EventDataset(), lambda e: e.jets().Count())")
    assert ast.dump(r) == ast.dump(expected.body[0].value)


@pytest.mark.parametrize("operation", ["ThenBy", "ThenByDescending"])
def test_then_by_normalized_chain(operation):
    ordered = my_event().OrderByDescending("lambda e: e.primary")
    result = getattr(ordered, operation)("lambda e: e.secondary").ThenBy("lambda e: e.third")
    expected = (
        ast.parse(
            f"ThenBy({operation}(OrderByDescending(EventDataset(), lambda e: e.primary), "
            "lambda e: e.secondary), lambda e: e.third)"
        )
        .body[0]
        .value
    )
    assert ast.dump(result.query_ast) == ast.dump(expected)
    assert result.item_type == ordered.item_type


@pytest.mark.parametrize("operation", ["ThenBy", "ThenByDescending"])
def test_then_by_requires_ordering(operation):
    with pytest.raises(ValueError, match="immediately follow an ordering"):
        getattr(my_event(), operation)("lambda e: e.key")
    with pytest.raises(ValueError, match="immediately follow an ordering"):
        getattr(my_event().OrderBy("lambda e: e.key").Where("lambda e: True"), operation)(
            "lambda e: e.key"
        )
    with pytest.raises(ValueError):
        getattr(my_event().OrderBy("lambda e: e.key"), operation)("10")


def test_order_by_rejects_non_lambda_expression():
    with pytest.raises(Exception):
        my_event().OrderBy("10")


def test_metadata():
    r = (
        my_event()
        .MetaData({"one": "two", "two": "three"})
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .query_ast
    )
    assert isinstance(r, ast.AST)


def test_metadata_duplicate_removed_in_value_async():
    r = (
        my_event()
        .MetaData({"one": "two"})
        .MetaData({"one": "two"})
        .Select("lambda e: e")
        .clean_ast()
    )

    assert isinstance(r, ast.AST)
    assert ast.dump(r).count("MetaData") == 1


def test_metadata_duplicate_removed_from_type_replacement_and_user_metadata():
    r = (
        my_event_with_type()
        .MetaData({"hi": "there"})
        .SelectMany(lambda e: e.Jets("jets"))
        .clean_ast()
    )

    assert isinstance(r, ast.AST)
    assert ast.dump(r).count("MetaData") == 1


def test_metadata_non_duplicate_payloads_retained_in_value_async():
    r = (
        my_event()
        .MetaData({"one": "two"})
        .MetaData({"three": "four"})
        .Select("lambda e: e")
        .query_ast
    )

    assert isinstance(r, ast.AST)
    assert ast.dump(r).count("MetaData") == 2


def test_clean_ast_removes_empty_and_duplicate_metadata():
    stream = my_event().MetaData({}).MetaData({"one": "two"}).MetaData({"one": "two"})

    cleaned = stream.clean_ast()

    assert isinstance(cleaned, ast.AST)
    assert ast.dump(cleaned).count("MetaData") == 1


def test_clean_ast_does_not_mutate_original_ast():
    stream = my_event().MetaData({"one": "two"}).MetaData({"one": "two"})

    _ = stream.clean_ast()

    assert ast.dump(stream.query_ast).count("MetaData") == 2


def test_query_metadata():
    r = (
        my_event()
        .QMetaData({"one": "two", "two": "three"})
        .SelectMany("lambda e: e.jets()")
        .Select("lambda j: j.pT()")
        .query_ast
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
        .query_ast
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
        .query_ast
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
        .query_ast
    )
    assert isinstance(r, ast.AST)
    assert "Select(source" not in ast.dump(r)


def test_query_with_comprehensions():
    r = (
        my_event()
        .Where("lambda e: [j.pT()>10 for j in e.jets].Count() > 0")
        .SelectMany("lambda e: e.jets()")
        .query_ast
    )
    assert isinstance(r, ast.AST)
    assert "ListComp" not in ast.dump(r)


def test_non_imported_function_call():
    r = (
        my_event()
        .Select(lambda event: np.cos(event.MET_phi))  # type: ignore # noqa
        .Where(lambda p: p > 0.0)
        .query_ast
    )  # NOQA
    assert isinstance(r, ast.AST)
    function = r.args[0].args[1].body.func
    assert isinstance(function, ast.Attribute) and function.attr == "cos"
    assert isinstance(function.value, ast.Name) and function.value.id == "np"
    assert isinstance(function.ctx, ast.Load)
    assert isinstance(function.value.ctx, ast.Load)


def test_imported_function_call():
    import numpy as np

    r = my_event().Select(lambda event: np.cos(event.MET_phi)).Where(lambda p: p > 0.0).query_ast
    assert isinstance(r, ast.AST)
    function = r.args[0].args[1].body.func
    assert isinstance(function, ast.Attribute) and function.attr == "cos"
    assert isinstance(function.value, ast.Name) and function.value.id == "np"
    assert isinstance(function.ctx, ast.Load)
    assert isinstance(function.value.ctx, ast.Load)


def test_bad_where():
    with pytest.raises(ValueError):
        my_event().Where("lambda e: 10").SelectMany("lambda e: e.jets()").query_ast


def test_ast_prop():
    r = my_event().SelectMany("lambda e: e.jets()").Select("lambda j: j.pT()")

    assert isinstance(r.query_ast, ast.AST)
    assert isinstance(r.query_ast, ast.Call)


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
