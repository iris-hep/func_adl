import ast
from typing import Tuple, cast

from astunparse import unparse
from func_adl.ast.function_simplifier import (FuncADLIndexError,
                                              make_args_unique,
                                              simplify_chained_calls)
from tests.util_debug_ast import normalize_ast

from .utils import reset_ast_counters  # NOQA


def util_process(ast_in, ast_out):
    '''Make sure ast in is the same as out after running through - this is a utility routine for
    the harness'''

    # Make sure the arguments are ok
    a_source = ast_in if isinstance(ast_in, ast.AST) else ast.parse(ast_in)
    a_expected = ast_out if isinstance(ast_out, ast.AST) else ast.parse(ast_out)

    a_updated_raw = simplify_chained_calls().visit(a_source)

    s_updated = ast.dump(normalize_ast().visit(a_updated_raw), annotate_fields=False,
                         include_attributes=False)
    s_expected = ast.dump(normalize_ast().visit(a_expected), annotate_fields=False,
                          include_attributes=False)

    print(s_updated)
    print(s_expected)
    assert s_updated == s_expected
    return a_updated_raw


##############
# Test lambda copier
def util_run_parse(a_text: str) -> Tuple[ast.Lambda, ast.Lambda]:
    module = ast.parse(a_text)
    assert isinstance(module, ast.Module)
    s = cast(ast.Expr, module.body[0])
    a = s.value
    assert isinstance(a, ast.Lambda)
    new_a = make_args_unique(a)
    return (a, new_a)


def test_lambda_copy_simple():
    a, new_a = util_run_parse('lambda a: a')
    assert unparse(new_a).strip() == "(lambda arg_0: arg_0)"
    assert ast.dump(new_a) != ast.dump(a)


def test_lambda_copy_no_arg():
    a, new_a = util_run_parse('lambda: 1+1')
    assert unparse(new_a).strip() == "(lambda : (1 + 1))"
    assert a is not new_a


def test_lambda_copy_nested():
    a, new_a = util_run_parse('lambda a: (lambda b: b)(a)')
    assert unparse(new_a).strip() == "(lambda arg_0: (lambda b: b)(arg_0))"


def test_lambda_copy_nested_same_arg_name():
    a, new_a = util_run_parse('lambda a: (lambda a: a)(a)')
    assert unparse(new_a).strip() == "(lambda arg_0: (lambda a: a)(arg_0))"


def test_lambda_copy_nested_captured():
    a, new_a = util_run_parse('lambda b: (lambda a: a+b)')
    assert unparse(new_a).strip() == "(lambda arg_0: (lambda a: (a + arg_0)))"


################
# Test convolutions
def test_function_replacement():
    util_process('(lambda x: x+1)(z)', 'z+1')


def test_function_convolution_2deep():
    util_process('(lambda x: x+1)((lambda y: y)(z))', 'z+1')


def test_function_convolution_2deep_same_names():
    util_process('(lambda x: x+1)((lambda x: x+2)(z))', 'z+2+1')


def test_function_convolution_3deep():
    util_process('(lambda x: x+1)((lambda y: y)((lambda z: z)(a)))', 'a+1')


# Testing out Select from the start
#
def test_select_simple():
    # Select statement shouldn't be altered on its own.
    util_process("Select(jets, lambda j: j*2)", "Select(jets, lambda j: j*2)")


def test_select_select_convolution():
    util_process('Select(Select(jets, lambda j: j*2), lambda j2: j2*2)',
                 'Select(jets, lambda j2: j2*2*2)')


def test_select_select_convolution_with_first():
    util_process('Select(Select(events, lambda e: First(e.jets)), lambda j: j.pt())',
                 'Select(events, lambda e: First(e.jets).pt())')


def test_select_identity():
    util_process('Select(jets, lambda j: j)', 'jets')

# Test out Where


def test_where_simple():
    util_process('Where(jets, lambda j: j.pt>10)', 'Where(jets, lambda j: j.pt>10)')


def test_where_always_true():
    util_process('Where(jets, lambda j: True)', 'jets')


def test_where_where():
    util_process('Where(Where(jets, lambda j: j.pt>10), lambda j1: j1.eta < 4.0)',
                 'Where(jets, lambda j: (j.pt>10) and (j.eta < 4.0))')


def test_where_select():
    util_process('Where(Select(jets, lambda j: j.pt), lambda p: p > 40)',
                 'Select(Where(jets, lambda j: j.pt > 40), lambda k: k.pt)')


def test_where_first():
    util_process('Where(Select(Select(events, lambda e: First(e.jets)), '
                 'lambda j: j.pt()), lambda jp: jp>40.0)',
                 'Select(Where(events, lambda e: First(e.jets).pt() > 40.0), '
                 'lambda e1: First(e1.jets).pt())')


# Testing out SelectMany
def test_selectmany_simple():
    # SelectMany statement shouldn't be altered on its own.
    util_process("SelectMany(jets, lambda j: j.tracks)", "SelectMany(jets, lambda j: j.tracks)")


def test_selectmany_where():
    a = util_process("Where(Select(SelectMany(jets, lambda j: j.tracks), "
                     "lambda z: z.pt()), lambda k: k>40)",
                     "SelectMany(jets, lambda e: Select(Where(e.tracks, "
                     "lambda t: t.pt()>40), lambda k: k.pt()))")
    print(ast.dump(a))
    # Make sure the z.pT() was a deep copy, not a shallow one.
    zpt_first = a.body[0].value.args[1].body.args[0].args[1].body.left
    zpt_second = a.body[0].value.args[1].body.args[1].body
    assert zpt_first is not zpt_second
    assert zpt_first.func is not zpt_second.func


def test_selectmany_select():
    # This example feels contrived, but that is because it is built to exercise just one part of
    # the transform. This feature becomes important when dealing with lists (in a monad). There is
    # a test below which combines this tranform with a tuple index, which is the common usecase
    # you see in the wild.
    util_process("SelectMany(Select(events, lambda e: Select(e.jets, lambda j: j.pt())), "
                 "lambda jetpts: jetpts)",
                 "SelectMany(events, lambda e: Select(e.jets, lambda j: j.pt()))")


def test_selectmany_selectmany():
    util_process("SelectMany(SelectMany(events, lambda e: e.jets), lambda j: j.tracks)",
                 "SelectMany(events, lambda e: SelectMany(e.jets, lambda j: j.tracks))")

# Testing first


# Tuple tests
def test_tuple_select():
    # (t1, t2)[0] should be t1.
    util_process('(t1,t2)[0]', 't1')


def test_list_select():
    # [t1, t2][0] should be t1.
    util_process('[t1,t2][0]', 't1')


def test_tuple_select_past_end():
    # This should cause a crash!
    try:
        util_process('(t1,t2)[3]', '0')
        assert False
    except FuncADLIndexError:
        pass


def test_tuple_in_lambda():
    util_process('(lambda t: t[0])((j1, j2))', 'j1')


def test_tuple_in_lambda_2deep():
    util_process('(lambda t: t[0])((lambda s: s[1])((j0, (j1, j2))))', 'j1')


def test_tuple_around_first():
    util_process('Select(events, lambda e: First(Select(e.jets, lambda j: (j, e)))[0])',
                 'Select(events, lambda e: First(e.jets))')


def test_tuple_in_SelectMany_Select():
    # A more common use of the SelectMany_Select transform.
    util_process("SelectMany(Select(events, "
                 "lambda e: (Select(e.jets, lambda j: j.pt()), e.eventNumber)), "
                 "lambda jetpts: jetpts[0])",
                 "SelectMany(events, lambda e: Select(e.jets, lambda j: j.pt()))")


def test_tuple_with_lambda_args_duplication():
    util_process("Select(Select(events, lambda e: (e.eles, e.muosn)), "
                 "lambda e: e[0].Select(lambda e: e.E()))",
                 "Select(events, lambda e: e.eles.Select(lambda e: e.E()))")


def test_tuple_with_lambda_args_duplication_rename():
    # Note that "g" below could still be "e" and it wouldn't tickle the bug. f and e need to be
    # #different.
    util_process("Select(Select(events, lambda e: (e.eles, e.muosn)), "
                 "lambda f: f[0].Select(lambda g: g.E()))",
                 "Select(events, lambda e: e.eles.Select(lambda e: e.E()))")
