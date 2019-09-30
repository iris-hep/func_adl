# Debug tools to help with AST's.
import ast
from sys import stdout


class pretty_print_visitor(ast.NodeVisitor):
    r'''
    An AST pretty-printer. Mostly used during debugging and testing.
    '''
    def __init__(self, stream):
        self._s = stream
        self._indent = 1

    def print_fields (self, node):
        'Handle different types of fields'
        if isinstance(node, list):
            self._s.write('    '*self._indent + '[\n')
            self._indent += 1
            for f in node:
                self.print_fields(f)
                self._s.write(',\n')
            self._indent -= 1
            self._s.write('    '*self._indent + ']\n')
        elif isinstance(node, ast.AST):
            first = True
            for field, value in ast.iter_fields(node):
                if not first:
                    self._s.write(',\n')
                first = False

                self._s.write('    '*self._indent + field + "=")
                self._indent += 1
                self.visit(value)
                self._indent -= 1
        elif node is None:
            pass
        else:
            self._s.write(str(node))

    def count_fields(self, node):
        'How many fields are there down a level?'
        if isinstance(node, list):
            return len(node)
        elif isinstance(node, ast.AST):
            return len(list(ast.iter_fields(node)))
        elif node is None:
            return 0
        else:
            return 0

    def generic_visit(self, node):
        self._s.write(node.__class__.__name__)
        self._s.write('(')
        if self.count_fields(node) > 0:
            self._s.write('\n')
            self.print_fields (node)
            self._s.write('    '*self._indent)
        self._s.write(')')

    def visit_Num(self, node):
        self._s.write('Num(n={0})'.format(node.n))

    def visit_str(self, node):
        self._s.write('"{0}"'.format(node))

    def visit_Name(self, node):
        self._s.write('Name(id="{0}")'.format(node.id))

def pretty_print (ast):
    'Pretty print an ast'
    pretty_print_visitor(stdout).visit(ast)
    stdout.write("\n")

class normalize_ast(ast.NodeTransformer):
    '''
    The AST's can have the same symantec meaning, but not the same text, so the string compare that happens as part of these tests fail. The code
    here's job is to make the ast produced by the local code look like the python code.
    '''
    def __init__ (self):
        self._arg_index = 0
        self._arg_transformer = []

    def push_stack_frame(self):
        self._arg_transformer.append({})

    def pop_stack_frame(self):
        del self._arg_transformer[-1]

    def new_arg(self):
        'Generate a new argument, in a nice order'
        old_arg = self._arg_index
        self._arg_index += 1
        return "t_arg_{0}".format(old_arg)

    def visit_Lambda(self, node: ast.Lambda) -> ast.Lambda:
        'Arguments need a uniform naming'
        a_mapping = [(a.arg, self.new_arg()) for a in node.args.args]

        # Remap everything that is inside this guy
        self.push_stack_frame()
        for m in a_mapping:
            self._arg_transformer[-1][m[0]] = m[1]
        body = self.visit(node.body)
        self.pop_stack_frame()

        # Rebuild the lambda guy
        args = [ast.arg(arg=m[1]) for m in a_mapping]
        return ast.Lambda(args=args, body=body)

    def lookup_name(self, name: str) -> str:
        for frames in reversed(self._arg_transformer):
            if name in frames:
                return frames[name]
        return name

    def visit_Name(self, node: ast.Name):
        return self.lookup_name(node.id)

