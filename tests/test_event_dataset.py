import ast
from typing import Any, cast

from func_adl import EventDataset


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
