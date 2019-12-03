# Test out the utility classes.
from func_adl.ast.func_adl_ast_utils import FuncADLNodeTransformer, FuncADLNodeVisitor, change_extension_functions_to_calls, is_call_of
import ast


class my_call_catcher(FuncADLNodeTransformer):
    def __init__ (self):
        self.count = 0
        self.args = []
        self.call_order = []

    def call_dude(self, node, args):
        self.count += 1
        self.args = args
        return node

    def call_dude1(self, node, args):
        self.call_order += ['dude1']
        for a in args:
            self.visit(a)
        return node

    def call_dude2(self, node, args):
        self.call_order += ['dude2']
        for a in args:
            self.visit(a)


def test_node_transform_method_ast():
    start = ast.parse('a.dude()')
    expected = ast.dump(start)
    e = FuncADLNodeTransformer()
    assert expected == ast.dump(e.visit(start))

def test_node_transform_method_ast_with_object():
    start = ast.parse('a.dude()')
    expected = ast.dump(start)
    e = my_call_catcher()
    assert expected == ast.dump(e.visit(start))
    assert e.count == 0

def test_node_transform_function_ast_with_object():
    start = ast.parse('dude()')
    expected = ast.dump(start)
    e = my_call_catcher()
    assert expected == ast.dump(e.visit(start))
    assert e.count == 1

def test_node_transform_function_ast_with_object_args():
    start = ast.parse('dude(10)')
    expected = ast.dump(start)
    e = my_call_catcher()
    assert expected == ast.dump(e.visit(start))
    assert e.count == 1
    assert len(e.args) == 1
    assert isinstance(e.args[0], ast.Num)
    assert e.args[0].n == 10

def test_node_transform_function_ast_with_object_args_norec():
    start = ast.parse('dude1(10)')
    expected = ast.dump(start)
    e = my_call_catcher()
    assert expected == ast.dump(e.visit(start))
    assert e.count == 0

def test_node_transform_function_deep():
    start = ast.parse('dork(dude(10))')
    expected = ast.dump(start)
    e = my_call_catcher()
    assert expected == ast.dump(e.visit(start))
    assert e.count == 1

def test_node_transform_arguments_only_done_last():
    start = ast.parse("dude2(10, 20, dude1(10))")
    e = my_call_catcher()
    e.visit(start)
    dude_order = e.call_order
    assert len(dude_order) == 2
    assert dude_order[0] == 'dude2'
    assert dude_order[1] == 'dude1'

def _parse_ast (e : str) -> ast.AST:
    a = ast.parse(e)
    b = a.body[0]
    assert isinstance(b, ast.Expr)
    return b.value

def test_is_call_to_expected_function():
    start = _parse_ast('dude(10)')
    assert is_call_of(start, 'dude')

def test_is_call_to_unexpected_function():
    start = _parse_ast('dude(10)')
    assert not is_call_of(start, 'dude1')

def test_is_call_to_expected_method():
    start = _parse_ast('a.dude(10)')
    assert not is_call_of(start, 'dude')

def test_is_call_not_a_call():
    start = _parse_ast('dude1')
    assert not is_call_of(start, 'dude1')

class my_call_vcatcher(FuncADLNodeVisitor):
    def __init__ (self):
        self.count = 0
        self.args = []
        self.call_order = []

    def call_dude(self, node, args):
        self.count += 1
        self.args = args
        return 42

    def call_dude1(self, node, args):
        self.call_order += ['dude1']
        for a in args:
            self.visit(a)
    
    def call_dude2(self, node, args):
        self.call_order += ['dude2']
        for a in args:
            self.visit(a)


def test_node_visit_method_ast_with_object():
    start = ast.parse('a.dude()')
    e = my_call_vcatcher()
    e.visit(start)
    assert e.count == 0

def test_node_visit_function_ast_with_object():
    start = ast.parse('dude()')
    e = my_call_vcatcher()
    e.visit(start)
    assert e.count == 1

def test_node_visit_with_return():
    start = ast.parse('dude()')
    e = my_call_vcatcher()
    r = e.visit(start.body[0].value)
    assert r == 42

def test_node_visit_function_ast_with_object_args():
    start = ast.parse('dude(10)')
    e = my_call_vcatcher()
    e.visit(start)
    assert e.count == 1
    assert len(e.args) == 1
    assert isinstance(e.args[0], ast.Num)
    assert e.args[0].n == 10

def test_node_visit_function_ast_with_object_args_norec():
    start = ast.parse('dude1(10)')
    e = my_call_vcatcher()
    e.visit(start)
    assert e.count == 0

def test_node_visit_function_deep():
    start = ast.parse('dork(dude(10))')
    e = my_call_vcatcher()
    e.visit(start)
    assert e.count == 1

def test_node_visit_arguments_only_done_last():
    start = ast.parse("dude2(10, 20, dude1(10))")
    e = my_call_vcatcher()
    e.visit(start)
    dude_order = e.call_order
    assert len(dude_order) == 2
    assert dude_order[0] == 'dude2'
    assert dude_order[1] == 'dude1'

### Parsing exetnsion functions into calls

def test_extension_functions_call():
    source = ast.parse("dude()")
    expected = ast.parse("dude()")

    transform = change_extension_functions_to_calls(source)
    assert ast.dump(transform) == ast.dump(expected)

def test_extension_functions_select_call():
    source = ast.parse("Select(jets, lambda b: b.pt())")
    expected = ast.parse("Select(jets, lambda b: b.pt())")

    transform = change_extension_functions_to_calls(source)
    assert ast.dump(transform) == ast.dump(expected)

def test_extension_functions_select_extension():
    source = ast.parse("jets.Select(lambda b: b.pt())")
    expected = ast.parse("Select(jets, lambda b: b.pt())")

    transform = change_extension_functions_to_calls(source)
    assert ast.dump(transform) == ast.dump(expected)

def test_extension_functions_select_extension_in_lambda_too():
    source = ast.parse("jets.Select(lambda b: b.Select(lambda j: jpt()))")
    expected = ast.parse("Select(jets, lambda b: Select(b, lambda j: jpt()))")

    transform = change_extension_functions_to_calls(source)
    assert ast.dump(transform) == ast.dump(expected)