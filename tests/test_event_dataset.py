import ast
from typing import Any, cast

import pytest

from func_adl import EventDataset, find_EventDataset
from func_adl.object_stream import ObjectStream


def test_cannot_create():
    with pytest.raises(Exception):
        # This should cause an abstract method error
        EventDataset()  # type: ignore


class my_event(EventDataset):
    async def execute_result_async(self, a: ast.AST) -> Any:
        return 10


class my_event_extra_args(EventDataset):
    def __init__(self):
        super().__init__()
        cast(ast.Call, self.query_ast).args.append(ast.Constant(value="hi"))

    async def execute_result_async(self, a: ast.AST) -> Any:
        return 10


def test_can_create():
    my_event()


def test_string_rep():
    e = my_event()
    assert str(e) == "my_event"
    assert repr(e) == "'my_event'"


def test_eds_recovery():
    "Make sure we can get back the event dataset"
    r = my_event()
    found_node = find_EventDataset(r.query_ast)
    assert hasattr(found_node, "_eds_object")
    assert found_node._eds_object == r  # type: ignore


def test_eds_recovery_with_select():
    r = my_event()
    q = r.Select(lambda a: a + 1)
    found_node = find_EventDataset(q.query_ast)
    assert found_node._eds_object == r  # type: ignore


def test_eds_recovery_two_ds():
    r1 = my_event()
    r2 = my_event()

    q1 = r1.Select(lambda a: a + 1)
    q2 = r2.Select(lambda b: b + 1)

    q = ObjectStream(ast.BinOp(q1.query_ast, ast.Add, q2.query_ast))  # type: ignore
    with pytest.raises(Exception) as e:
        find_EventDataset(q.query_ast)

    assert "more than one" in str(e)


def test_eds_recovery_no_root():
    q = ObjectStream(ast.BinOp(ast.Constant(1), ast.Add, ast.Constant(2)))  # type: ignore
    with pytest.raises(Exception) as e:
        find_EventDataset(q.query_ast)

    assert "no root" in str(e)


def test_eds_recovery_with_odd_call():
    r = my_event()
    q = r.Select(lambda a: (lambda b: b + 1)(a))
    found_node = find_EventDataset(q.query_ast)
    assert found_node._eds_object == r  # type: ignore
