from func_adl.ast.function_simplifier import FuncADLIndexError
from tests.util_debug_ast import util_process
import ast

################
# Test convolutions
def test_function_replacement():
    util_process('(lambda x: x+1)(z)', 'z+1')

def test_function_convolution_2deep():
    util_process('(lambda x: x+1)((lambda y: y)(z))', 'z+1')

def test_function_convolution_3deep():
    util_process('(lambda x: x+1)((lambda y: y)((lambda z: z)(a)))', 'a+1')

################
# Testing out Select from the start
#
def test_select_simple():
    # Select statement shouldn't be altered on its own.
    util_process("Select(jets, lambda j: j*2)", "Select(jets, lambda j: j*2)")

def test_select_select_convolution():
    util_process('Select(Select(jets, lambda j: j*2), lambda j2: j2*2)', 'Select(jets, lambda j2: j2*2*2)')

def test_select_select_convolution_with_first():
    util_process('Select(Select(events, lambda e: First(e.jets)), lambda j: j.pt())', 'Select(events, lambda e: First(e.jets).pt())')

def test_select_identity():
    util_process('Select(jets, lambda j: j)', 'jets')

################
# Test out Where
def test_where_simple():
    util_process('Where(jets, lambda j: j.pt>10)', 'Where(jets, lambda j: j.pt>10)')

def test_where_always_true():
    util_process('Where(jets, lambda j: True)', 'jets')

def test_where_where():
    util_process('Where(Where(jets, lambda j: j.pt>10), lambda j1: j1.eta < 4.0)', 'Where(jets, lambda j: (j.pt>10) and (j.eta < 4.0))')

def test_where_select():
    util_process('Where(Select(jets, lambda j: j.pt), lambda p: p > 40)', 'Select(Where(jets, lambda j: j.pt > 40), lambda k: k.pt)')

def test_where_first():
    util_process('Where(Select(Select(events, lambda e: First(e.jets)), lambda j: j.pt()), lambda jp: jp>40.0)', \
        'Select(Where(events, lambda e: First(e.jets).pt() > 40.0), lambda e1: First(e1.jets).pt())')
 
################
# Testing out SelectMany
def test_selectmany_simple():
    # SelectMany statement shouldn't be altered on its own.
    util_process("SelectMany(jets, lambda j: j.tracks)", "SelectMany(jets, lambda j: j.tracks)")

def test_selectmany_where():
    a = util_process("Where(Select(SelectMany(jets, lambda j: j.tracks), lambda z: z.pt()), lambda k: k>40)",
        "SelectMany(jets, lambda e: Select(Where(e.tracks, lambda t: t.pt()>40), lambda k: k.pt()))")
    print(ast.dump(a))
    # Make sure the z.pT() was a deep copy, not a shallow one.
    zpt_first = a.body[0].value.args[1].body.args[0].args[1].body.left
    zpt_second = a.body[0].value.args[1].body.args[1].body
    assert zpt_first is not zpt_second
    assert zpt_first.func is not zpt_second.func

def test_selectmany_select():
    util_process("SelectMany(Select(events, lambda e: e.jets), lambda j: j.pt())",
                      "SelectMany(events, lambda e: Select(e.jets, lambda j: j.pt()))")

def test_selectmany_selectmany():
    util_process("SelectMany(SelectMany(events, lambda e: e.jets), lambda j: j.tracks)",
                 "SelectMany(events, lambda e: SelectMany(e.jets, lambda j: j.tracks))")

###############
# Testing first

################
# Tuple tests
def test_tuple_select():
    # (t1, t2)[0] should be t1.
    util_process('(t1,t2)[0]', 't1')

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
    util_process('Select(events, lambda e: First(Select(e.jets, lambda j: (j, e)))[0])', 'Select(events, lambda e: First(e.jets))')