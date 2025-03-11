import ast
import inspect
from dataclasses import is_dataclass
from typing import Any, List

from func_adl.util_ast import lambda_build


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
                    raise ValueError(
                        f"Comprehension variable must be a name, but found {target}"
                        f" - {ast.unparse(node)}."
                    )
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
                a = self.resolve_generator(a.elt, a.generators, node)

            return a

        def visit_GeneratorExp(self, node: ast.GeneratorExp) -> Any:
            "Translate a generator into a Select statement"
            a = self.generic_visit(node)

            if isinstance(a, ast.GeneratorExp):
                a = self.resolve_generator(a.elt, a.generators, node)

            return a

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
            return a

    return syntax_transformer().visit(a)
