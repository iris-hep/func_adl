from func_adl.ast.aggregate_shortcuts import aggregate_node_transformer
from tests.util_debug_ast import normalize_ast
import ast


def util_process(ast_in, ast_out):
    """Make sure ast in is the same as out after running through - this is a utility routine
    for the harness"""

    # Make sure the arguments are ok
    a_source = ast_in if isinstance(ast_in, ast.AST) else ast.parse(ast_in)
    a_expected = ast_out if isinstance(ast_out, ast.AST) else ast.parse(ast_out)

    a_updated_raw = aggregate_node_transformer().visit(a_source)

    s_updated = ast.dump(
        normalize_ast().visit(a_updated_raw), annotate_fields=False, include_attributes=False
    )
    s_expected = ast.dump(
        normalize_ast().visit(a_expected), annotate_fields=False, include_attributes=False
    )

    print(s_updated)
    print(s_expected)
    assert s_updated == s_expected
    return a_updated_raw


def test_plain_sequence():
    util_process("a", "a")


def test_len_of_sequence():
    util_process("len(a)", "Aggregate(a, 0, lambda acc, v: acc+1)")


def test_count_of_sequence():
    util_process("Count(a)", "Aggregate(a, 0, lambda acc, v: acc+1)")


def test_sum_of_sequence():
    util_process("Sum(a)", "Aggregate(a, 0, lambda acc, v: acc+v)")


def test_min_of_sequence():
    util_process("Min(a)", "Aggregate(a, 0, lambda acc, v: acc if acc < v else v)")


def test_max_of_sequence():
    util_process("Max(a)", "Aggregate(a, 0, lambda acc, v: acc if acc > v else v)")


def test_sum_in_argument():
    util_process(
        "Min(Sum(a))",
        "Aggregate(Aggregate(a, 0, lambda acc, v: acc+v), 0, lambda acc, "
        "v: acc if acc < v else v)",
    )


def test_sum_in_labmda():
    util_process(
        "ResultTTree(Select(EventDataset(), lambda e: Sum(Select(e.TruthParticles, "
        "lambda t: t.prodVtx().x())), ['n_jets'], 'root.root'))",
        "ResultTTree(Select(EventDataset(), lambda e: Aggregate(Select(e.TruthParticles, "
        "lambda t: t.prodVtx().x()), 0, lambda acc, v: acc + v), ['n_jets'], "
        "'root.root'))",
    )
