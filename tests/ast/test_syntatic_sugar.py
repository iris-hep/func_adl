import ast

import pytest

from func_adl.ast.syntatic_sugar import resolve_syntatic_sugar


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
