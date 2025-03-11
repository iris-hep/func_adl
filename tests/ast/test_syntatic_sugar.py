import ast
from dataclasses import dataclass

import pytest

from func_adl import ObjectStream
from func_adl.ast.syntatic_sugar import resolve_syntatic_sugar
from func_adl.util_ast import parse_as_ast


def test_resolve_normal_expression():
    a = ast.parse("Select(jets, lambda j: j.pt())")
    a_new = resolve_syntatic_sugar(a)

    assert ast.dump(a) == ast.dump(a_new)


def test_resolve_listcomp():
    a = ast.parse("[j.pt() for j in jets]")
    a_new = resolve_syntatic_sugar(a)

    assert ast.dump(ast.parse("jets.Select(lambda j: j.pt())")) == ast.dump(a_new)


def test_resolve_generator():
    a = ast.parse("(j.pt() for j in jets)")
    a_new = resolve_syntatic_sugar(a)

    assert ast.dump(ast.parse("jets.Select(lambda j: j.pt())")) == ast.dump(a_new)


def test_resolve_listcomp_if():
    a = ast.parse("[j.pt() for j in jets if j.pt() > 100]")
    a_new = resolve_syntatic_sugar(a)

    assert ast.dump(
        ast.parse("jets.Where(lambda j: j.pt() > 100).Select(lambda j: j.pt())")
    ) == ast.dump(a_new)


def test_resolve_listcomp_2ifs():
    a = ast.parse("[j.pt() for j in jets if j.pt() > 100 if abs(j.eta()) < 2.4]")
    a_new = resolve_syntatic_sugar(a)

    assert ast.dump(
        ast.parse(
            "jets.Where(lambda j: j.pt() > 100).Where(lambda j: abs(j.eta()) < 2.4)"
            ".Select(lambda j: j.pt())"
        )
    ) == ast.dump(a_new)


def test_resolve_2generator():
    a = ast.parse("(j.pt()+e.pt() for j in jets for e in electrons)")
    a_new = resolve_syntatic_sugar(a)

    assert ast.dump(
        ast.parse("jets.Select(lambda j: electrons.Select(lambda e: j.pt()+e.pt()))")
    ) == ast.dump(a_new)


def test_resolve_bad_iterator():
    a = ast.parse("[j.pt() for idx,j in enumerate(jets)]")

    with pytest.raises(ValueError) as e:
        resolve_syntatic_sugar(a)

    assert "name" in str(e)


def test_resolve_no_async():
    a = ast.parse("[j.pt() async for j in enumerate(jets)]")

    with pytest.raises(ValueError) as e:
        resolve_syntatic_sugar(a)

    assert "can't be async" in str(e)


class LocalJet:
    def pt(self) -> float:
        return 0.0


def test_resolve_dataclass_no_args():
    "Make sure a dataclass becomes a dictionary"

    @dataclass
    class dc_1:
        x: ObjectStream[LocalJet]
        y: ObjectStream[LocalJet]

    a = parse_as_ast(lambda e: dc_1(e.Jets(), e.Electrons()).x.Select(lambda j: j.pt())).body
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("{'x': e.Jets(), 'y': e.Electrons()}.x.Select(lambda j: j.pt())")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_dataclass_named_args():
    "Make sure a dataclass becomes a dictionary"

    @dataclass
    class dc_1:
        x: ObjectStream[LocalJet]
        y: ObjectStream[LocalJet]

    a = parse_as_ast(lambda e: dc_1(x=e.Jets(), y=e.Electrons()).x.Select(lambda j: j.pt())).body
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("{'x': e.Jets(), 'y': e.Electrons()}.x.Select(lambda j: j.pt())")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_dataclass_mixed_args():
    "Make sure a dataclass becomes a dictionary"

    @dataclass
    class dc_1:
        x: ObjectStream[LocalJet]
        y: ObjectStream[LocalJet]

    a = parse_as_ast(lambda e: dc_1(e.Jets(), y=e.Electrons()).x.Select(lambda j: j.pt())).body
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("{'x': e.Jets(), 'y': e.Electrons()}.x.Select(lambda j: j.pt())")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_dataclass_too_few_args():
    "Make sure a dataclass becomes a dictionary"

    @dataclass
    class dc_1:
        x: ObjectStream[LocalJet]
        y: ObjectStream[LocalJet]

    a = parse_as_ast(lambda e: dc_1(e.Jets()).x.Select(lambda j: j.pt())).body  # type: ignore
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("{'x': e.Jets()}.x.Select(lambda j: j.pt())")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_dataclass_too_many_args():
    "Make sure a dataclass becomes a dictionary"

    @dataclass
    class dc_1:
        x: ObjectStream[LocalJet]
        y: ObjectStream[LocalJet]

    with pytest.raises(ValueError):
        a = parse_as_ast(
            lambda e: dc_1(e.Jets(), e.Electrons(), e.Muons(), e.Jets()).x.Select(  # type: ignore
                lambda j: j.pt()
            )  # type: ignore
        ).body
        resolve_syntatic_sugar(a)


def test_resolve_dataclass_bad_args():
    "Make sure a dataclass becomes a dictionary"

    @dataclass
    class dc_1:
        x: ObjectStream[LocalJet]
        y: ObjectStream[LocalJet]

    with pytest.raises(ValueError):
        a = parse_as_ast(
            lambda e: dc_1(z=e.Jets()).x.Select(lambda j: j.pt())  # type: ignore
        ).body
        resolve_syntatic_sugar(a)
