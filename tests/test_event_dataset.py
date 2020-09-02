import ast
from typing import Any

import pytest

from func_adl import EventDataset
from func_adl.event_dataset import find_ed_in_ast

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
        self._ast.args.append(ast.Str(s='hi'))

    async def execute_result_async(self, a: ast.AST) -> Any:
        return 10


def test_can_create():
    my_event()


def test_find_event_at_top():
    e = my_event()
    assert find_ed_in_ast(e._ast) is e


def test_find_event_inside():
    e = my_event()
    add = ast.BinOp(ast.Num(5), ast.Add, e._ast)
    assert find_ed_in_ast(add) is e


def test_find_event_with_more_ast():
    e = my_event_extra_args()
    add = ast.BinOp(ast.Num(5), ast.Add, e._ast)
    assert find_ed_in_ast(add) is e


def test_string_rep():
    e = my_event()
    assert str(e) == "my_event"
    assert repr(e) == "'my_event'"