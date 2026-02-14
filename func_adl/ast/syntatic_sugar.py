import ast
import copy
import inspect
from dataclasses import is_dataclass
from itertools import product
from typing import Any, Dict, List, Optional, Tuple

from func_adl.util_ast import as_ast, lambda_build


def resolve_syntatic_sugar(a: ast.AST) -> ast.AST:
    """Transforms python idioms into func_adl statements where it makes sense

    * List comprehensions are turned into `Select` statements
    * Generator expressions are turned into `Select` statements
    * A data class is converted into a dictionary.

    Args:
        a (ast.AST): The AST to scan for syntatic sugar

    Returns:
        ast.AST: The resolved syntax
    """

    class syntax_transformer(ast.NodeTransformer):
        def _extract_literal_iterable(self, node: ast.AST) -> Optional[List[ast.expr]]:
            """Return literal iterable elements if ``node`` is a list/tuple literal."""

            if isinstance(node, (ast.List, ast.Tuple)):
                return list(node.elts)
            if isinstance(node, ast.Constant) and isinstance(node.value, (list, tuple)):
                return [as_ast(v) for v in node.value]
            return None

        def _target_bindings(
            self, target: ast.AST, value: ast.AST, node: ast.AST
        ) -> Optional[Dict[str, ast.expr]]:
            """Build loop-variable bindings for a single comprehension iteration.

            Returns ``None`` when destructuring cannot be applied for this ``value``.
            """

            if isinstance(target, ast.Name):
                return {target.id: copy.deepcopy(value)}

            if isinstance(target, (ast.Tuple, ast.List)):
                if not isinstance(value, (ast.Tuple, ast.List)):
                    return None
                if len(target.elts) != len(value.elts):
                    raise ValueError(
                        "Comprehension unpacking length mismatch" f" - {ast.unparse(node)}"
                    )

                bindings: Dict[str, ast.expr] = {}
                for target_elt, value_elt in zip(target.elts, value.elts):
                    child_bindings = self._target_bindings(target_elt, value_elt, node)
                    if child_bindings is None:
                        return None
                    bindings.update(child_bindings)
                return bindings

            raise ValueError(
                f"Comprehension variable must be a name or tuple/list, but found {target}"
                f" - {ast.unparse(node)}"
            )

        def _substitute_names(self, expr: ast.expr, bindings: Dict[str, ast.expr]) -> ast.expr:
            class _name_replacer(ast.NodeTransformer):
                def __init__(self, loop_bindings: Dict[str, ast.expr]):
                    self._loop_bindings = loop_bindings

                def visit_Name(self, replace_node: ast.Name) -> Any:
                    if (
                        isinstance(replace_node.ctx, ast.Load)
                        and replace_node.id in self._loop_bindings
                    ):
                        return copy.deepcopy(self._loop_bindings[replace_node.id])
                    return replace_node

            return _name_replacer(bindings).visit(copy.deepcopy(expr))

        def _inline_literal_comprehension(
            self, lambda_body: ast.expr, generators: List[ast.comprehension], node: ast.AST
        ) -> Optional[List[ast.expr]]:
            """Expand comprehensions over literal iterables into literal expressions."""

            literal_values: List[List[Tuple[Dict[str, ast.expr], List[ast.expr]]]] = []
            for generator in generators:
                if generator.is_async:
                    raise ValueError(f"Comprehension can't be async - {ast.unparse(node)}.")

                iter_values = self._extract_literal_iterable(generator.iter)
                if iter_values is None:
                    return None

                generator_values: List[Tuple[Dict[str, ast.expr], List[ast.expr]]] = []
                for iter_value in iter_values:
                    bindings = self._target_bindings(generator.target, iter_value, node)
                    if bindings is None:
                        return None
                    generator_values.append((bindings, generator.ifs))
                literal_values.append(generator_values)

            if len(literal_values) == 0:
                return []

            expanded: List[ast.expr] = []
            for combo in product(*literal_values):
                merged_bindings: Dict[str, ast.expr] = {}
                all_ifs: List[ast.expr] = []
                for c_bindings, c_ifs in combo:
                    merged_bindings.update(c_bindings)
                    all_ifs.extend(c_ifs)

                include_item = True
                for if_clause in all_ifs:
                    rendered_if = self.visit(self._substitute_names(if_clause, merged_bindings))
                    if not isinstance(rendered_if, ast.Constant) or not isinstance(
                        rendered_if.value, bool
                    ):
                        raise ValueError(
                            "Literal comprehension if-clause must resolve to a bool constant"
                            f" - {ast.unparse(if_clause)}"
                        )
                    if not rendered_if.value:
                        include_item = False
                        break

                if include_item:
                    rendered_item = self.visit(
                        self._substitute_names(lambda_body, merged_bindings)
                    )
                    assert isinstance(rendered_item, ast.expr)
                    expanded.append(rendered_item)

            return expanded

        def _resolve_any_all_call(
            self, call_node: ast.Call, source_node: ast.AST
        ) -> Optional[ast.AST]:
            """Translate `any`/`all` on list or tuple literals into boolean operations."""

            func_name: Optional[str] = None
            if isinstance(call_node.func, ast.Name):
                func_name = call_node.func.id
            elif isinstance(call_node.func, ast.Constant) and callable(call_node.func.value):
                if call_node.func.value in [any, all]:
                    func_name = call_node.func.value.__name__

            if func_name not in ["any", "all"]:
                return None

            if len(call_node.args) != 1 or len(call_node.keywords) > 0:
                raise ValueError(
                    f"{func_name} requires exactly one positional argument"
                    f" - {ast.unparse(source_node)}"
                )

            sequence = call_node.args[0]
            if isinstance(sequence, (ast.ListComp, ast.GeneratorExp)):
                return None
            if not isinstance(sequence, (ast.List, ast.Tuple)):
                raise ValueError(
                    f"{func_name} requires a list or tuple literal argument"
                    f" - {ast.unparse(source_node)}"
                )

            if len(sequence.elts) == 0:
                return ast.Constant(value=(func_name == "all"))

            return ast.BoolOp(
                op=ast.Or() if func_name == "any" else ast.And(),
                values=sequence.elts,
            )

        def resolve_generator(
            self, lambda_body: ast.expr, generators: List[ast.comprehension], node: ast.AST
        ) -> ast.AST:
            """Translate a list comprehension or a generator to Select statements.

            `[j.pt() for j in jets] -> jets.Select(lambda j: j.pt())`

            Args:
                lambda_body (ast.AST): The target of the lambda expression
                generators (List[ast.comprehension]): The list of generators
                node (ast.AST): The original AST node

            Returns:
                ast.AST: The reformed ast (untouched if no expression detected)
            """
            a = node
            for c in reversed(generators):
                target = c.target
                if not isinstance(target, ast.Name):
                    # Keep original comprehension for unsupported lowering cases.
                    return node
                if c.is_async:
                    raise ValueError(f"Comprehension can't be async - {ast.unparse(node)}.")
                source_collection = c.iter

                # Turn the if clauses into Where statements
                for a_if in c.ifs:
                    where_function = lambda_build(target.id, a_if)
                    source_collection = ast.Call(
                        func=ast.Attribute(attr="Where", value=source_collection, ctx=ast.Load()),
                        args=[where_function],
                        keywords=[],
                    )

                lambda_function = lambda_build(target.id, lambda_body)
                a = ast.Call(
                    func=ast.Attribute(attr="Select", value=source_collection, ctx=ast.Load()),
                    args=[lambda_function],
                    keywords=[],
                )

                # In case we have chained comprehensions
                lambda_body = a
            return a

        def visit_ListComp(self, node: ast.ListComp) -> Any:
            "Translate a list comprehension into a Select statement"
            a = self.generic_visit(node)

            if isinstance(a, ast.ListComp):
                if (
                    expanded := self._inline_literal_comprehension(a.elt, a.generators, node)
                ) is not None:
                    return ast.List(elts=expanded, ctx=ast.Load())
                a = self.resolve_generator(a.elt, a.generators, node)

            return a

        def visit_GeneratorExp(self, node: ast.GeneratorExp) -> Any:
            "Translate a generator into a Select statement"
            a = self.generic_visit(node)

            if isinstance(a, ast.GeneratorExp):
                if (
                    expanded := self._inline_literal_comprehension(a.elt, a.generators, node)
                ) is not None:
                    return ast.List(elts=expanded, ctx=ast.Load())
                a = self.resolve_generator(a.elt, a.generators, node)

            return a

        def visit_Compare(self, node: ast.Compare) -> Any:
            """Expand membership tests of an expression against a constant list
            or tuple/set into a series of comparisons.

            ``x in [1, 2]`` becomes ``x == 1 or x == 2``.
            """

            a = self.generic_visit(node)

            if not isinstance(a, ast.Compare):
                return a

            if len(a.ops) != 1 or not isinstance(a.ops[0], (ast.In, ast.NotIn)):
                return a

            left = a.left
            right = a.comparators[0]

            def const_list(t: ast.AST) -> Optional[List[ast.Constant]]:
                if isinstance(t, (ast.List, ast.Tuple, ast.Set)):
                    if all(isinstance(e, ast.Constant) for e in t.elts):
                        return list(t.elts)  # type: ignore
                    raise ValueError(
                        "All elements in comparison list/tuple/set must be constants"
                        f" - {ast.unparse(t)}"
                    )
                return None

            elements = const_list(right)
            expr = left
            if elements is None:
                raise ValueError(
                    f"Right side of 'in' must be a list, tuple, or set - {ast.unparse(node)}"
                )

            is_in = isinstance(a.ops[0], ast.In)
            return ast.BoolOp(
                op=ast.Or() if is_in else ast.And(),
                values=[
                    ast.Compare(
                        left=copy.deepcopy(expr),
                        ops=[ast.Eq() if is_in else ast.NotEq()],
                        comparators=[copy.deepcopy(e)],
                    )
                    for e in elements
                ],
            )

        def convert_call_to_dict(
            self, a: ast.Call, node: ast.AST, sig_arg_names: List[str]
        ) -> ast.AST:
            """Translate a data class into a dictionary.

            Args:
                a (ast.Call): The call node representing the data class instantiation
                node (ast.AST): The original AST node

            Returns:
                ast.AST: The reformed AST as a dictionary
            """
            if len(sig_arg_names) < (len(a.args) + len(a.keywords)):
                assert isinstance(a.func, ast.Constant)
                raise ValueError(
                    f"Too many arguments for dataclass {a.func.value} - {ast.unparse(node)}."
                )

            arg_values = a.args
            arg_names = [ast.Constant(value=n) for n in sig_arg_names[: len(arg_values)]]
            arg_lookup = {a.arg: a.value for a in a.keywords}
            for name in sig_arg_names[len(arg_values) :]:
                if name in arg_lookup:
                    arg_values.append(arg_lookup[name])
                    arg_names.append(ast.Constant(value=name))

            for name in arg_lookup.keys():
                if name not in sig_arg_names:
                    assert isinstance(a.func, ast.Constant)
                    raise ValueError(
                        f"Argument {name} not found in dataclass {a.func.value}"
                        f" - {ast.unparse(node)}."
                    )

            return ast.Dict(
                keys=arg_names,  # type: ignore
                values=arg_values,
            )

        def _merge_into(self, target: ast.expr, add: ast.Dict) -> ast.expr:
            """Merge ``add`` dictionary into ``target`` which may itself be a
            dictionary or an if-expression containing dictionaries."""

            if isinstance(target, ast.Dict):
                return ast.Dict(keys=target.keys + add.keys, values=target.values + add.values)
            else:
                return target

        def visit_Dict(self, node: ast.Dict) -> Any:
            """Flatten ``**`` expansions in dictionary literals.

            If the starred expression is a dictionary it is merged directly.  If
            the expression is an ``if`` with both branches being dictionaries and
            the test is a constant, it is resolved at transformation time.  If
            the test is not resolvable, an error is raised as the back end cannot
            translate it."""

            a = self.generic_visit(node)
            assert isinstance(a, ast.Dict)

            base_keys: List[Optional[ast.expr]] = []
            base_values: List[ast.expr] = []
            expansions: List[ast.expr] = []
            for k, v in zip(a.keys, a.values):
                if k is None:
                    expansions.append(v)
                else:
                    base_keys.append(k)
                    base_values.append(v)

            result: ast.AST = ast.Dict(keys=base_keys, values=base_values)

            for e in expansions:
                if isinstance(e, ast.Dict):
                    result = self._merge_into(result, e)
                elif (
                    isinstance(e, ast.IfExp)
                    and isinstance(e.body, ast.Dict)
                    and isinstance(e.orelse, ast.Dict)
                ):
                    if isinstance(e.test, ast.Constant):
                        branch = e.body if bool(e.test.value) else e.orelse
                        result = self._merge_into(result, branch)
                    else:
                        raise ValueError(
                            "Conditional dictionary expansion requires a constant test"
                            f" - {ast.unparse(e)}"
                        )
                else:
                    return a

            return result

        def visit_Call(self, node: ast.Call) -> Any:
            """
            This method checks if the call is to a dataclass or a named tuple and converts
            the call to a dictionary representation if so.

            Args:
                node (ast.Call): The AST Call node to visit.
            Returns:
                Any: The transformed node if it matches the criteria, otherwise the original node.
            """
            a = self.generic_visit(node)

            if isinstance(a, ast.Call) and isinstance(a.func, ast.Constant):
                if is_dataclass(a.func.value):
                    assert isinstance(a.func, ast.Constant)

                    # We have a dataclass. Turn it into a dictionary
                    signature = inspect.signature(a.func.value)  # type: ignore
                    sig_arg_names = [p.name for p in signature.parameters.values()]

                    return self.convert_call_to_dict(a, node, sig_arg_names)

                elif hasattr(a.func.value, "_fields"):
                    # We have a named tuple. Turn it into a dictionary
                    arg_names = [n for n in a.func.value._fields]

                    return self.convert_call_to_dict(a, node, arg_names)

            if isinstance(a, ast.Call):
                any_all_call = self._resolve_any_all_call(a, node)
                if any_all_call is not None:
                    return any_all_call
            return a

    return syntax_transformer().visit(a)
