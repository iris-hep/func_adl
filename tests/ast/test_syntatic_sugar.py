import ast
from collections import namedtuple
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


def test_resolve_named_tuple_no_args():
    "Make sure a named tuple becomes a dictionary"

    nt_1 = namedtuple("nt_1", ["x", "y"])

    a = parse_as_ast(lambda e: nt_1(e.Jets(), e.Electrons()).x.Select(lambda j: j.pt())).body
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("{'x': e.Jets(), 'y': e.Electrons()}.x.Select(lambda j: j.pt())")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_named_tuple_typed():
    "Make sure a named tuple becomes a dictionary"

    from typing import NamedTuple

    class nt_1(NamedTuple):
        x: ObjectStream[LocalJet]
        y: ObjectStream[LocalJet]

    a = parse_as_ast(lambda e: nt_1(e.Jets(), e.Electrons()).x.Select(lambda j: j.pt())).body
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("{'x': e.Jets(), 'y': e.Electrons()}.x.Select(lambda j: j.pt())")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_named_tuple_too_few_args():
    "Make sure a named tuple becomes a dictionary"

    nt_1 = namedtuple("nt_1", ["x", "y"])

    a = parse_as_ast(lambda e: nt_1(e.Jets()).x.Select(lambda j: j.pt())).body  # type: ignore
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("{'x': e.Jets()}.x.Select(lambda j: j.pt())")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_named_tuple_too_many_args():
    "Make sure a named tuple becomes a dictionary"

    nt_1 = namedtuple("nt_1", ["x", "y"])

    with pytest.raises(ValueError):
        a = parse_as_ast(
            lambda e: nt_1(e.Jets(), e.Electrons(), e.Muons(), e.Jets()).x.Select(  # type: ignore
                lambda j: j.pt()
            )  # type: ignore
        ).body
        resolve_syntatic_sugar(a)


def test_resolve_named_tuple_kwards():
    "Make sure a named tuple becomes a dictionary"

    nt_1 = namedtuple("nt_1", ["x", "y"])

    a = parse_as_ast(lambda e: nt_1(x=e.Jets(), y=e.Electrons()).x.Select(lambda j: j.pt())).body
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("{'x': e.Jets(), 'y': e.Electrons()}.x.Select(lambda j: j.pt())")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_random_class():
    "A regular class should not be resolved"

    class nt_1:
        x: ObjectStream[LocalJet]
        y: ObjectStream[LocalJet]

    a = parse_as_ast(
        lambda e: nt_1(x=e.Jets(), y=e.Electrons()).x.Select(lambda j: j.pt())  # type: ignore
    ).body
    a_resolved = resolve_syntatic_sugar(a)

    assert "nt_1(" in ast.unparse(a_resolved)


def test_resolve_compare_list_in():
    a = ast.parse("p.absPdgId() in [35, 51]")
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("p.absPdgId() == 35 or p.absPdgId() == 51")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_compare_tuple_in():
    a = ast.parse("p.absPdgId() in (35, 51)")
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("p.absPdgId() == 35 or p.absPdgId() == 51")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_compare_list_non_constant():
    a = ast.parse("p.absPdgId() in [x, 51]")
    with pytest.raises(ValueError, match="All elements"):
        resolve_syntatic_sugar(a)


def test_resolve_compare_list_wrong_order():
    a = ast.parse("[31, 51] in p.absPdgId()")
    with pytest.raises(ValueError, match="Right side"):
        resolve_syntatic_sugar(a)


def test_resolve_dict_star_merge():
    """Dictionary unpacking should be flattened"""

    a = ast.parse("{'n': e.EventNumber(), **{'m': e.EventNumber()}}").body[0].value  # type: ignore
    a_resolved = resolve_syntatic_sugar(a)

    expected = (
        ast.parse("{'n': e.EventNumber(), 'm': e.EventNumber()}").body[0].value  # type: ignore
    )
    assert ast.unparse(a_resolved) == ast.unparse(expected)


def test_resolve_dict_star_ifexp_true():
    """Conditional dictionary unpacking should resolve when condition is True"""

    a = (
        ast.parse("{'n': e.EventNumber(), **({'m': e.EventNumber()} if True else {})}")
        .body[0]
        .value  # type: ignore
    )
    a_resolved = resolve_syntatic_sugar(a)

    expected = (
        ast.parse("{'n': e.EventNumber(), 'm': e.EventNumber()}").body[0].value  # type: ignore
    )
    assert ast.unparse(a_resolved) == ast.unparse(expected)


def test_resolve_dict_star_ifexp_false():
    """Conditional dictionary unpacking should resolve when condition is False"""

    a = (
        ast.parse("{'n': e.EventNumber(), **({'m': e.EventNumber()} if False else {})}")
        .body[0]
        .value  # type: ignore
    )
    a_resolved = resolve_syntatic_sugar(a)

    expected = ast.parse("{'n': e.EventNumber()}").body[0].value  # type: ignore
    assert ast.unparse(a_resolved) == ast.unparse(expected)


def test_resolve_dict_star_ifexp_unknown():
    """Unresolvable conditions should result in an error"""

    a = (
        ast.parse("{'n': e.EventNumber(), **({'m': e.EventNumber()} if cond else {})}")
        .body[0]
        .value  # type: ignore
    )
    with pytest.raises(ValueError):
        resolve_syntatic_sugar(a)
