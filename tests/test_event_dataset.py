import ast
from typing import Any, cast

import pytest

from func_adl import EventDataset

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
        cast(ast.Call, self.query_ast).args.append(ast.Str(s='hi'))

    async def execute_result_async(self, a: ast.AST) -> Any:
        return 10


def test_can_create():
    my_event()


def test_string_rep():
    e = my_event()
    assert str(e) == "my_event"
    assert repr(e) == "'my_event'"
