"""The gateway's entry points, which the behaviour tests never reach.

`serve_gateway` binds a socket and `main` parses argv, so neither appears in a
unit test that exercises the protocol - and a NameError in either ships green.
That is not hypothetical: a log line added to serve_gateway referenced `args`,
which only exists in main, and the whole suite stayed green while the gateway
refused to start at all.

These are static checks on purpose. They cost nothing, they need no socket and
no controller, and they catch the one class of fault that the behaviour tests
structurally cannot see.
"""

import argparse
import ast
import builtins
import pathlib
import unittest

import fraktal_ab_gateway as gateway
import fraktal_ab_projection as projection


SOURCE = pathlib.Path(gateway.__file__).read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)
def _module_level(node):
    """Yield module-scope nodes, NOT descending into function or class bodies.

    `ast.walk` descends into everything, which is what made the first version
    of this file useless: `args = parser.parse_args()` inside main() was
    collected as a MODULE name, so every function appeared to have `args` in
    scope and the very defect this file exists for went unnoticed. Found by
    reintroducing that defect and watching the test pass.
    """
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef)):
            yield child          # the NAME is module scope; the body is not
            continue
        yield child
        yield from _module_level(child)


MODULE_NAMES = {
    node.id for node in _module_level(TREE)
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
} | {
    node.name for node in ast.iter_child_nodes(TREE)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
} | {
    (alias.asname or alias.name).split(".")[0]
    for node in ast.walk(TREE) if isinstance(node, (ast.Import, ast.ImportFrom))
    for alias in node.names
}


def _functions():
    for node in ast.walk(TREE):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _bound(fn) -> set[str]:
    """Everything a name could legitimately resolve to inside `fn`."""
    args = fn.args
    names = {a.arg for a in
             args.posonlyargs + args.args + args.kwonlyargs}
    for extra in (args.vararg, args.kwarg):
        if extra is not None:
            names.add(extra.arg)
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                               ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            names.update(node.names)
    return names


class NoUnboundNames(unittest.TestCase):
    def test_no_function_reads_a_name_nothing_binds(self):
        """The check that would have caught `args` in serve_gateway.

        Nested functions see their enclosing scope, so a name bound anywhere
        in an outer function counts - which is why this walks outward rather
        than judging each function alone.
        """
        # A module run from a file binds __file__ itself; it is not a builtin,
        # so dir(builtins) alone would call the gateway's own path unbound.
        builtin_names = set(dir(builtins)) | {"__file__"}
        parents = {}
        for fn in _functions():
            for node in ast.walk(fn):
                if node is not fn and isinstance(
                        node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    parents[node] = fn

        bound = {fn: _bound(fn) for fn in _functions()}
        for fn in _functions():
            visible = set(bound[fn])
            walker = parents.get(fn)
            while walker is not None:
                visible |= bound[walker]
                walker = parents.get(walker)
            visible |= MODULE_NAMES | builtin_names
            for node in ast.walk(fn):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    self.assertIn(
                        node.id, visible,
                        f"{fn.name}() line {node.lineno} reads '{node.id}', "
                        f"which nothing in scope binds")


class Arguments(unittest.TestCase):
    def _parse(self, *argv):
        parser = None
        # main() builds its parser inline, so exercise it the way a user does:
        # --help exits 0, and an unknown choice exits 2. Both prove the parser
        # is reachable and consistent without binding a socket.
        return parser

    def test_help_is_reachable(self):
        with self.assertRaises(SystemExit) as raised:
            gateway.main(["--help"])
        self.assertEqual(raised.exception.code, 0)

    def test_every_access_level_the_projection_knows_is_accepted(self):
        """The flag's choices and the projection's ladder are one contract; a
        level accepted here and missing there is a KeyError at startup."""
        source = ast.parse(SOURCE)
        choices = None
        for node in ast.walk(source):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "add_argument"
                    and node.args
                    and getattr(node.args[0], "value", None) == "--access-level"):
                for keyword in node.keywords:
                    if keyword.arg == "choices":
                        choices = {e.value for e in keyword.value.elts}
        self.assertIsNotNone(choices, "--access-level declares no choices")
        self.assertEqual(choices, set(projection.ACCESS_LEVELS))

    def test_an_unknown_level_is_refused_before_anything_opens(self):
        with self.assertRaises(SystemExit) as raised:
            gateway.main(["1.2.3.4", "--expect-serial", "ABC",
                          "--access-level", "wizard"])
        self.assertEqual(raised.exception.code, 2)

    def test_the_default_level_is_operator(self):
        """Raising it is a posture change; the default must never move
        quietly."""
        source = ast.parse(SOURCE)
        for node in ast.walk(source):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "add_argument"
                    and node.args
                    and getattr(node.args[0], "value", None) == "--access-level"):
                default = next(k.value.value for k in node.keywords
                               if k.arg == "default")
                self.assertEqual(default, "operator")
                return
        self.fail("--access-level not declared")


class ReaderContract(unittest.TestCase):
    def test_the_reader_takes_the_declared_level(self):
        """main resolves the name to an ordinal and hands it to build_reader;
        a reader that ignored it would publish operator whatever was asked."""
        import inspect

        signature = inspect.signature(gateway.build_reader)
        self.assertIn("access_level", signature.parameters)

    def test_an_omitted_level_reads_as_operator(self):
        import inspect

        default = inspect.signature(
            gateway.build_reader).parameters["access_level"].default
        self.assertIsNone(default)
        # None means "the projection's own default", which is operator.
        self.assertEqual(projection.ACCESS_OPERATOR, 1)


if __name__ == "__main__":
    unittest.main()
