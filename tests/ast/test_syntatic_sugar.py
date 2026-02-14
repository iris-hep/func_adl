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


def test_resolve_literal_list_comp():
    a = ast.parse("[i for i in [1, 2, 3]]")
    a_new = resolve_syntatic_sugar(a)

    assert ast.dump(ast.parse("[1, 2, 3]")) == ast.dump(a_new)


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
    a_new = resolve_syntatic_sugar(a)

    # Unsupported lowering (tuple target with non-literal source) should be
    # preserved for downstream processing.
    assert ast.unparse(a_new) == ast.unparse(a)


def test_resolve_no_async():
    a = ast.parse("[j.pt() async for j in enumerate(jets)]")

    with pytest.raises(ValueError) as e:
        resolve_syntatic_sugar(a)

    assert "can't be async" in str(e)


class LocalJet:
    def pt(self) -> float:
        return 0.0


def keep_high_pt(j: LocalJet) -> bool:
    return j.pt() > 10


def jet_pt(j: LocalJet) -> float:
    return j.pt()


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


def test_resolve_compare_set_in():
    a = ast.parse("p.absPdgId() in {35, 51}")
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("p.absPdgId() == 35 or p.absPdgId() == 51")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_compare_set_not_in():
    a = ast.parse("p.absPdgId() not in {35, 51}")
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("p.absPdgId() != 35 and p.absPdgId() != 51")
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
    with pytest.raises(ValueError, match="Conditional dictionary"):
        resolve_syntatic_sugar(a)


def test_resolve_dict_star_ifexp_nested():
    """Nested conditional dictionary unpacking should resolve correctly"""

    a = (
        ast.parse(
            "{'n': e.EventNumber(), **({'m': e.EventNumber(), **({'o': e.EventNumber()} "
            "if True else {})} if True else {})}"
        )
        .body[0]
        .value  # type: ignore
    )
    a_resolved = resolve_syntatic_sugar(a)

    expected = (
        ast.parse("{'n': e.EventNumber(), 'm': e.EventNumber(), 'o': e.EventNumber()}")
        .body[0]
        .value  # type: ignore
    )
    assert ast.unparse(a_resolved) == ast.unparse(expected)


def test_resolve_any_list():
    a = ast.parse("any([e.pt() > 10, e.eta() < 2.4])")
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("e.pt() > 10 or e.eta() < 2.4")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_all_tuple():
    a = ast.parse("all((e.pt() > 10, e.eta() < 2.4))")
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("e.pt() > 10 and e.eta() < 2.4")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_any_empty_is_false():
    a = ast.parse("any([])")
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("False")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_all_empty_is_true():
    a = ast.parse("all([])")
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("True")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_any_requires_literal_sequence():
    a = ast.parse("any(items)")

    with pytest.raises(ValueError, match="list or tuple literal"):
        resolve_syntatic_sugar(a)


def test_resolve_any_generator_from_literal_capture():
    bib_triggers = [(1, 2), (3, 4)]

    def tdt_chain_fired(chain: int) -> bool:
        return chain > 1

    a = parse_as_ast(
        lambda e: any(
            tdt_chain_fired(incl_trig) and not tdt_chain_fired(bib_trig)
            for incl_trig, bib_trig in bib_triggers
        )
    )
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("lambda e: (1 > 1 and not (2 > 1)) or (3 > 1 and not (4 > 1))")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_any_generator_to_query_count_comparison():
    a = ast.parse("any(j.pt() > 10 for j in e.jets)")
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("e.jets.Where(lambda j: j.pt() > 10).Count() > 0")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_filter_lambda_to_where():
    a = ast.parse("filter(lambda j: j.pt() > 10, e.jets)")
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("e.jets.Where(lambda j: j.pt() > 10)")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_map_lambda_to_select():
    a = ast.parse("map(lambda j: j.pt(), e.jets)")
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("e.jets.Select(lambda j: j.pt())")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_filter_captured_callable_to_where():
    a = parse_as_ast(lambda e: filter(keep_high_pt, e.jets))
    a_resolved = resolve_syntatic_sugar(a)

    assert isinstance(a_resolved, ast.Lambda)
    assert isinstance(a_resolved.body, ast.Call)
    assert isinstance(a_resolved.body.func, ast.Attribute)
    assert a_resolved.body.func.attr == "Where"
    assert isinstance(a_resolved.body.args[0], ast.Lambda)
    all_name_ids = {n.id for n in ast.walk(a_resolved) if isinstance(n, ast.Name)}
    assert "keep_high_pt" not in all_name_ids


def test_resolve_map_captured_callable_to_select():
    a = parse_as_ast(lambda e: map(jet_pt, e.jets))
    a_resolved = resolve_syntatic_sugar(a)

    assert isinstance(a_resolved, ast.Lambda)
    assert isinstance(a_resolved.body, ast.Call)
    assert isinstance(a_resolved.body.func, ast.Attribute)
    assert a_resolved.body.func.attr == "Select"
    assert isinstance(a_resolved.body.args[0], ast.Lambda)
    all_name_ids = {n.id for n in ast.walk(a_resolved) if isinstance(n, ast.Name)}
    assert "jet_pt" not in all_name_ids


def test_resolve_map_lambda_body_still_applies_any_all_sugar():
    a = ast.parse("map(lambda j: any([j.pt() > 10, j.eta() < 2.4]), e.jets)")
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("e.jets.Select(lambda j: j.pt() > 10 or j.eta() < 2.4)")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_filter_map_rejects_invalid_signatures():
    with pytest.raises(ValueError, match="filter requires exactly two arguments"):
        resolve_syntatic_sugar(ast.parse("filter(lambda j: j.pt() > 10)"))

    with pytest.raises(ValueError, match="map only supports positional arguments"):
        resolve_syntatic_sugar(ast.parse("map(func=lambda j: j.pt(), seq=e.jets)"))

    with pytest.raises(ValueError, match="filter requires a lambda"):
        resolve_syntatic_sugar(ast.parse("filter(predicate, e.jets)"))


def test_resolve_all_generator_with_if_clause_to_query_count_comparison():
    a = ast.parse("all(j.pt() > 10 for j in e.jets if j.eta() < 2.4)")
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse(
        "e.jets.Where(lambda j: j.eta() < 2.4).Where(lambda j: not j.pt() > 10).Count() == 0"
    )
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_any_all_generator_empty_sequence_semantics():
    a_any = ast.parse("any(j.pt() > 10 for j in [])")
    a_any_resolved = resolve_syntatic_sugar(a_any)
    a_any_expected = ast.parse("False")

    a_all = ast.parse("all(j.pt() > 10 for j in [])")
    a_all_resolved = resolve_syntatic_sugar(a_all)
    a_all_expected = ast.parse("True")

    assert ast.unparse(a_any_resolved) == ast.unparse(a_any_expected)
    assert ast.unparse(a_all_resolved) == ast.unparse(a_all_expected)


def test_resolve_sum_generator_to_query_sum_call():
    a = ast.parse("sum(j.pt() for j in jets)")
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("Sum(jets.Select(lambda j: j.pt()))")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_sum_list_comprehension_to_query_sum_call():
    a = ast.parse("sum([j.pt() for j in jets])")
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("Sum(jets.Select(lambda j: j.pt()))")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_any_call_keeps_nested_sum_rewrite():
    a = ast.parse("any([sum(j.pt() for j in jets) > 0, e.met() > 20])")
    a_resolved = resolve_syntatic_sugar(a)

    a_expected = ast.parse("Sum(jets.Select(lambda j: j.pt())) > 0 or e.met() > 20")
    assert ast.unparse(a_resolved) == ast.unparse(a_expected)


def test_resolve_nested_captured_function_in_list_comp():
    bib_triggers = [(1, 2), (3, 4)]

    def tmt_match_object(trig: int, jet: int) -> bool:
        return trig > jet

    def is_trigger_jet(jet: int) -> bool:
        return any(tmt_match_object(trig, jet) for trig, _ in bib_triggers)

    a = parse_as_ast(lambda e: {"jet_is_trigger": [is_trigger_jet(j) for j in e.jets]})
    a_resolved = resolve_syntatic_sugar(a)
    all_name_ids = {n.id for n in ast.walk(a_resolved) if isinstance(n, ast.Name)}

    # Ensure helper calls and captures are fully inlined, so type inference
    # does not see unresolved names like `any`, `trig`, `_`, or `bib_triggers`.
    assert "any" not in all_name_ids
    assert "trig" not in all_name_ids
    assert "_" not in all_name_ids
    assert "bib_triggers" not in all_name_ids
