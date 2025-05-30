# Various node visitors to clean up nested function calls of various types.
import ast
import copy
from typing import List, Tuple, Union, cast

from func_adl.ast.call_stack import argument_stack, stack_frame
from func_adl.ast.func_adl_ast_utils import (
    FuncADLNodeTransformer,
    is_call_of,
    unpack_Call,
)
from func_adl.util_ast import (
    function_call,
    lambda_body,
    lambda_body_replace,
    lambda_build,
    lambda_call,
    lambda_is_identity,
    lambda_is_true,
    lambda_unwrap,
)

argument_var_counter = 0


def arg_name():
    "Return a unique name that can be used as an argument"
    global argument_var_counter
    n = "arg_{0}".format(argument_var_counter)
    argument_var_counter += 1
    return n


def make_args_unique(a: ast.Lambda) -> ast.Lambda:
    """
    Replaces the lambda with a new lambda, with unique arguments names

    Args:
        a       Lambda function to be copied over

    Returns:
        l       New copy of the lambda. The original is unmodified.
    """

    class replace_args(ast.NodeTransformer):
        def __init__(self):
            ast.NodeTransformer.__init__(self)
            self._arg_stack: List[Tuple[str, str]] = []
            self._seen_lambda = False

        def visit_Lambda(self, node: ast.Lambda) -> ast.Lambda:
            if self._seen_lambda:
                mapping = [(a.arg, a.arg) for a in node.args.args]
            else:
                mapping = [(a.arg, arg_name()) for a in node.args.args]
                self._seen_lambda = True

            for old, new in mapping:
                self._arg_stack.append((old, new))

            r = self.generic_visit(node)
            assert isinstance(r, ast.Lambda)

            r.args.args = [ast.arg(arg=new, annotation=None) for old, new in mapping]
            for arg in node.args.args:
                self._arg_stack.pop()

            return r

        def visit_Name(self, node: ast.Name) -> ast.Name:
            for n in reversed(self._arg_stack):
                if n[0] == node.id:
                    return ast.Name(id=n[1])
            return node

    return replace_args().visit(copy.deepcopy(a))


def convolute(ast_g: ast.Lambda, ast_f: ast.Lambda):
    "Return an AST that represents g(f(args))"
    # Combine the lambdas into a single call by calling g with f as an argument
    l_g = make_args_unique(lambda_unwrap(ast_g))
    l_f = make_args_unique(lambda_unwrap(ast_f))

    x = arg_name()
    f_arg = ast.Name(x, ast.Load())
    call_g = ast.Call(l_g, [ast.Call(l_f, [f_arg], [])], [])

    call_g_lambda = lambda_build(x, call_g)

    # Build a new call to nest the functions
    return call_g_lambda


def make_Select(source: ast.expr, selection: ast.expr):
    "Make a select, and return source is selection is an identity"
    return cast(
        ast.expr,
        (
            source
            if lambda_is_identity(selection)
            else function_call("Select", [source, selection])
        ),
    )


class FuncADLIndexError(Exception):
    """If we are doing an indexing operation and we are out of range, throw this."""

    def __init__(self, msg):
        Exception.__init__(self, msg)


def _is_method_call_on_first(node: ast.Call):
    """
    Determine if this is a call like First(seq).method(args).
    """
    if not isinstance(node.func, ast.Attribute):
        return False

    if not is_call_of(node.func.value, "First"):
        return False

    return True


class simplify_chained_calls(FuncADLNodeTransformer):
    """
    In order to cleanly evaluate things like tuples (which should not show up at the back end),
    we must move around various functions, evaluate others, etc., where we can. This AST
    transformer does that work.
    """

    def __init__(self):
        self._arg_stack = argument_stack()

    def visit_Select_of_Select(self, parent: ast.Call, selection: ast.Lambda):
        r"""
        seq.Select(x: f(x)).Select(y: g(y))
        => Select(Select(seq, x: f(x)), y: g(y))
        is turned into
        seq.Select(x: g(f(x)))
        => Select(seq, x: g(f(x)))
        """
        _, args = unpack_Call(parent)
        assert args is not None
        source = args[0]
        func_f = args[1]
        assert isinstance(func_f, ast.Lambda)
        func_g = selection

        # Convolute the two functions
        new_selection = self.visit(convolute(func_g, func_f))

        # And return the parent select with the new selection function
        return make_Select(source, new_selection)

    def visit_Select_of_SelectMany(self, parent, selection):
        r"""
        seq.SelectMany(x: f(x)).Select(y: g(y))
        => Select(SelectMany(seq, x: f(x)), y: g(y))
        is turned into
        seq.SelectMany(x: f(x).Select(y: g(y)))
        => SelectMany(seq, x: Select(f(x), y: g(y)))
        """
        (_, args) = unpack_Call(parent)
        assert args is not None
        source = args[0]
        func_f = args[1]
        assert isinstance(func_f, ast.Lambda)
        func_g = selection

        lambda_select = lambda_body_replace(
            func_f, make_Select(lambda_body(func_f), func_g)
        )  # type: ast.AST
        return self.visit(function_call("SelectMany", [source, lambda_select]))

    def call_Select(self, node: ast.Call, args: List[ast.AST]):
        r"""
        Transformation #1:
        seq.Select(x: f(x)).Select(y: g(y))
        => Select(Select(seq, x: f(x)), y: g(y))
        is turned into
        seq.Select(x: g(f(x)))
        => Select(seq, x: g(f(x)))

        Transformation #2:
        seq.SelectMany(x: f(x)).Select(y: g(y))
        => Select(SelectMany(seq, x: f(x)), y: g(y))
        is turned into
        seq.SelectMany(x: f(x).Select(y: g(y)))
        => SelectMany(seq, x: Select(f(x), y: g(y)))

        Transformation #3:
        seq.Where(x: f(x)).Select(y: g(y))
        => Select(Where(seq, x: f(x), y: g(y))
        is not altered.
        """
        source = args[0]
        transform = args[1]
        assert isinstance(transform, ast.Lambda)

        parent_select = self.visit(source)
        if is_call_of(parent_select, "Select"):
            return self.visit_Select_of_Select(parent_select, transform)
        elif is_call_of(parent_select, "SelectMany"):
            return self.visit_Select_of_SelectMany(parent_select, transform)
        else:
            selection = self.visit(transform)
            return make_Select(parent_select, selection)

    def visit_SelectMany_of_Select(self, parent_select: ast.Call, selection: ast.Lambda):
        """
        seq.Select(x: f(x)).SelectMany(y: g(y))
        => SelectMany(Select(seq, x: f(x)), y:g(y))
        is turned into
        seq.SelectMany(x: f(x).Select(y: g(y)))
        => SelectMany(seq, x: Select(f(x), y: g(y)))
        """
        _, select_args = unpack_Call(parent_select)
        assert (select_args is not None) and len(select_args) == 2
        seq = select_args[0]
        func_f = select_args[1]
        assert isinstance(func_f, ast.Lambda)
        func_g = selection

        w = function_call("SelectMany", [seq, self.visit(convolute(func_g, func_f))])
        return w

    def visit_SelectMany_of_SelectMany(self, parent: ast.Call, selection: ast.Lambda):
        """
        Transformation #1:
        seq.SelectMany(x: f(x)).SelectMany(y: f(y))
        => SelectMany(SelectMany(seq, x: f(x)), y: f(y))
        is turned into:
        seq.SelectMany(x: f(x).SelectMany(y: f(y)))
        => SelectMany(seq, x: SelectMany(f(x), y: f(y)))
        """
        _, args = unpack_Call(parent)
        assert (args is not None) and len(args) == 2
        seq = args[0]
        func_f = args[1]
        assert isinstance(func_f, ast.Lambda)
        func_g = selection

        captured_arg = func_f.args.args[0].arg
        captured_body = func_f.body
        new_select = function_call("SelectMany", [captured_body, func_g])
        new_select_lambda = lambda_build(captured_arg, new_select)
        new_select_many = function_call("SelectMany", [seq, new_select_lambda])
        return new_select_many

    def call_SelectMany(self, node: ast.Call, args: List[ast.AST]):
        r"""
        Transformation #1:
        seq.SelectMany(x: f(x)).SelectMany(y: f(y))
        => SelectMany(SelectMany(seq, x: f(x)), y: f(y))
        is turned into:
        seq.SelectMany(x: f(x).SelectMany(y: f(y)))
        => SelectMany(seq, x: SelectMany(f(x), y: f(y)))

        Transformation #2:
        seq.Select(x: f(x)).SelectMany(y: g(y))
        => SelectMany(Select(seq, x: f(x)), y:g(y))
        is turned into
        seq.SelectMany(x: g(f(x)))
        => SelectMany(seq, x: g(f(x)))

        Transformation #3:
        seq.Where(x: f(x)).SelectMany(y: g(y))
        """
        selection = args[1]
        assert isinstance(selection, ast.Lambda)
        parent_select = self.visit(args[0])
        if is_call_of(parent_select, "SelectMany"):
            return self.visit_SelectMany_of_SelectMany(parent_select, selection)
        elif is_call_of(parent_select, "Select"):
            return self.visit_SelectMany_of_Select(parent_select, selection)
        else:
            return function_call("SelectMany", [parent_select, self.visit(selection)])

    def visit_Where_of_Where(self, parent: ast.Call, filter: ast.Lambda):
        """
        seq.Where(x: f(x)).Where(x: g(x))
        => Where(Where(seq, x: f(x)), y: g(y))
        is turned into
        seq.Where(x: f(x) and g(y))
        => Where(seq, x: f(x) and g(y))
        """
        # Unpack arguments and f and g functions
        _, args = unpack_Call(parent)
        assert args is not None
        source = args[0]
        func_f = args[1]
        assert isinstance(func_f, ast.Lambda)
        func_g = filter

        arg = arg_name()
        convolution = lambda_build(
            arg, ast.BoolOp(ast.And(), [lambda_call(arg, func_f), lambda_call(arg, func_g)])
        )
        return self.visit(function_call("Where", [source, convolution]))

    def visit_Where_of_Select(self, parent, filter):
        """
        seq.Select(x: f(x)).Where(y: g(y))
        => Where(Select(seq, x: f(x)), y: g(y))
        Is turned into:
        seq.Where(x: g(f(x))).Select(x: f(x))
        => Select(Where(seq, x: g(f(x)), f(x))
        """
        _, args = unpack_Call(parent)
        assert args is not None
        source = args[0]
        func_f = args[1]
        assert isinstance(func_f, ast.Lambda)
        func_g = filter

        w = function_call("Where", [source, self.visit(convolute(func_g, func_f))])
        s = make_Select(w, func_f)

        # Recursively visit this mess to see if the Where needs to move further up.
        return self.visit(s)

    def visit_Where_of_SelectMany(self, parent, filter):
        """
        seq.SelectMany(x: f(x)).Where(y: g(y))
        => Where(SelectMany(seq, x: f(x)), y: g(y))
        Is turned into:
        seq.SelectMany(x: f(x).Where(y: g(y)))
        => SelectMany(seq, x: Where(f(x), g(y)))
        """
        _, args = unpack_Call(parent)
        assert args is not None
        seq = args[0]
        func_f = args[1]
        assert isinstance(func_f, ast.Lambda)

        func_g = filter
        lambda_where = lambda_body_replace(
            func_f, function_call("Where", [lambda_body(func_f), func_g])
        )

        return self.visit(function_call("SelectMany", [seq, lambda_where]))

    def call_Where(self, node: ast.Call, args: List[ast.AST]) -> ast.AST:
        r"""
        Transformation #1:
        seq.Where(x: f(x)).Where(x: g(x))
        => Where(Where(seq, x: f(x)), y: g(y))
        is turned into
        seq.Where(x: f(x) and g(y))
        => Where(seq, x: f(x) and g(y))

        Transformation #2:
        seq.Select(x: f(x)).Where(y: g(y))
        => Where(Select(seq, x: f(x)), y: g(y))
        Is turned into:
        seq.Where(x: g(f(x))).Select(x: f(x))
        => Select(Where(seq, x: g(f(x)), f(x))

        Transformation #3:
        seq.SelectMany(x: f(x)).Where(y: g(y))
        => Where(SelectMany(seq, x: f(x)), y: g(y))
        Is turned into:
        seq.SelectMany(x: f(x).Where(y: g(y)))
        => SelectMany(seq, x: Where(f(x), g(y)))
        """
        source = args[0]
        filter = args[1]
        assert isinstance(filter, ast.Lambda)

        parent_where = self.visit(source)
        if is_call_of(parent_where, "Where"):
            return self.visit_Where_of_Where(parent_where, filter)
        elif is_call_of(parent_where, "Select"):
            return self.visit_Where_of_Select(parent_where, filter)
        elif is_call_of(parent_where, "SelectMany"):
            return self.visit_Where_of_SelectMany(parent_where, filter)
        else:
            f = self.visit(filter)
            if lambda_is_true(f):
                return parent_where
            else:
                return function_call("Where", [parent_where, f])

    def select_method_call_on_first(self, node: ast.Call):
        """Turn
        First(seq).method(args)
        into
        First(Select(seq, s: s.method(args)))
        """
        # Extract the call info
        assert isinstance(node.func, ast.Attribute)
        method_name = node.func.attr
        method_args = node.args
        method_keywords = (
            node.keywords if hasattr(node, "keywords") else node.kwargs  # type: ignore
        )

        assert isinstance(node.func.value, ast.Call)
        seq = node.func.value.args[0]

        # Now rebuild the call
        a = arg_name()
        call_args = {
            "func": ast.Attribute(value=ast.Name(a, ast.Load()), attr=method_name),
            "args": method_args,
        }
        if hasattr(node, "keywords"):
            call_args["keywords"] = method_keywords
        else:
            call_args["kwargs"] = method_keywords

        seq_a_call = ast.Call(**call_args)
        select = make_Select(seq, lambda_build(a, seq_a_call))

        return self.visit(function_call("First", [select]))

    def visit_Call(self, call_node):
        """We are looking for cases where an argument is another function or expression.
        In that case, we want to try to get an evaluation of the argument, and replace it in the
        AST of this function. This only works of the function we are calling is a lambda.

        Also, if this is a First() call, then move the call inside it.
        """
        if type(call_node.func) is ast.Lambda:
            arg_asts = [self.visit(a) for a in call_node.args]
            with stack_frame(self._arg_stack):
                for a_name, arg in zip(call_node.func.args.args, arg_asts):
                    self._arg_stack.define_name(a_name.arg, arg)
                # Now, evaluate the expression, and then lift it.
                return self.visit(call_node.func.body)
        elif _is_method_call_on_first(call_node):
            return self.select_method_call_on_first(call_node)
        else:
            return FuncADLNodeTransformer.visit_Call(self, call_node)

    def visit_Subscript_Tuple(self, v: ast.Tuple, s: ast.Constant):
        """
        (t1, t2, t3...)[1] => t2

        Only works if index is a number
        """
        # Get the value out - this is due to supporting python 3.7-3.9
        n = s.value
        if n is None:
            return ast.Subscript(v, s, ast.Load())  # type: ignore
        assert isinstance(n, int), "Programming error: index is not an integer in tuple subscript"
        if n >= len(v.elts):
            raise FuncADLIndexError(
                f"Attempt to access the {n}th element of a tuple only"
                f" {len(v.elts)} values long."
            )

        return copy.deepcopy(v.elts[n])

    def visit_Subscript_List(self, v: ast.List, s: ast.Constant):
        """
        [t1, t2, t3...][1] => t2

        Only works if index is a number
        """
        n = s.value
        if n is None:
            return ast.Subscript(v, s, ast.Load())  # type: ignore
        if n >= len(v.elts):
            raise FuncADLIndexError(
                f"Attempt to access the {n}th element of a tuple"
                f" only {len(v.elts)} values long."
            )

        return copy.deepcopy(v.elts[n])

    def visit_Subscript_Dict(self, v: ast.Dict, s: ast.Constant):
        """
        {t1, t2, t3...}[1] => t2
        """
        sub = s.value
        assert isinstance(sub, (str, int))
        return self.visit_Subscript_Dict_with_value(v, sub)

    def visit_Subscript_Dict_with_value(self, v: ast.Dict, s: Union[str, int]):
        "Do the lookup for the dict"
        for index, value in enumerate(v.keys):
            assert isinstance(value, ast.Constant)
            if value.value == s:
                return copy.deepcopy(v.values[index])

        return ast.Subscript(v, s, ast.Load())  # type: ignore

    def visit_Subscript_Of_First(self, first: ast.expr, s):
        """
        Convert a seq.First()[0]
        ==>
        seq.Select(l: l[0]).First()

        Other work will do the conversion as needed.
        """

        # Build the select that starts from the source and does the slice.
        a = arg_name()
        select = make_Select(
            first, lambda_build(a, ast.Subscript(ast.Name(a, ast.Load()), s, ast.Load()))
        )

        return self.visit(function_call("First", [select]))

    def visit_Subscript(self, node):
        r"""
        Simple Reduction
        (t1, t2, t3...)[1] => t2

        Move [] past a First()
        seq.First()[0] => seq.Select(j: j[0]).First()
        """
        v = self.visit(node.value)
        s = self.visit(node.slice)
        if type(v) is ast.Tuple:
            return self.visit_Subscript_Tuple(v, s)
        if type(v) is ast.List:
            return self.visit_Subscript_List(v, s)
        if type(v) is ast.Dict:
            return self.visit_Subscript_Dict(v, s)

        if is_call_of(v, "First"):
            return self.visit_Subscript_Of_First(v.args[0], s)

        # Nothing interesting, so do the normal thing several levels down.
        return ast.Subscript(v, s, ast.Load())

    def visit_Name(self, name_node):
        "Do lookup and see if we should translate or not."
        return self._arg_stack.lookup_name(name_node.id, default=name_node)

    def visit_Attribute_Of_First(self, first: ast.expr, attr: str):
        """
        Convert a seq.First().attr
        ==>
        seq.Select(l: l.attr).First()

        Other work will do the conversion as needed.
        """

        # Build the select that starts from the source and does the slice.
        a = arg_name()
        select = make_Select(
            first, lambda_build(a, ast.Attribute(value=ast.Name(a, ast.Load()), attr=attr))
        )

        return self.visit(function_call("First", [select]))

    def visit_Attribute(self, node):
        """
        If this is a reference against a dict, then we can de-ref it if there is a key.
        Otherwise, we need to make sure to make a new version of the Attribute so it does
        not get reused'
        """
        if is_call_of(node.value, "First"):
            return self.visit_Attribute_Of_First(node.value.args[0], node.attr)  # type: ignore

        visited_value = self.visit(node.value)
        if isinstance(visited_value, ast.Dict):
            return self.visit_Subscript_Dict_with_value(visited_value, node.attr)

        return ast.Attribute(value=visited_value, attr=node.attr, ctx=ast.Load())
