"""Translate the MCP tool subset into source accepted by Max 2020 Python 2.7."""

import ast
import io
import tokenize


class Python2CompatibilityError(ValueError):
    """Raised when a tool uses syntax that cannot be represented in Python 2.7."""


class _Python2Transformer(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        node.returns = None
        args = node.args
        for arg in list(getattr(args, "posonlyargs", [])):
            arg.annotation = None
        for arg in args.args + args.kwonlyargs:
            arg.annotation = None
        if args.vararg:
            args.vararg.annotation = None
        if args.kwarg:
            args.kwarg.annotation = None
        return node

    def visit_AsyncFunctionDef(self, node):
        raise Python2CompatibilityError("async functions are not supported by Max 2020 Python 2.7")

    def visit_AnnAssign(self, node):
        self.generic_visit(node)
        value = node.value if node.value is not None else ast.Constant(value=None)
        return ast.copy_location(ast.Assign(targets=[node.target], value=value), node)

    def visit_JoinedStr(self, node):
        values = []

        def render_joined(joined):
            pieces = []
            for item in joined.values:
                if isinstance(item, ast.Constant) and isinstance(item.value, str):
                    pieces.append(item.value.replace("{", "{{").replace("}", "}}"))
                elif isinstance(item, ast.FormattedValue):
                    expression = self.visit(item.value)
                    conversion = item.conversion
                    if conversion == 97:
                        expression = ast.Call(
                            func=ast.Name(id="_mcp_ascii", ctx=ast.Load()),
                            args=[expression],
                            keywords=[],
                        )
                        conversion = -1
                    index = len(values)
                    values.append(expression)
                    field = "{" + str(index)
                    if conversion == 114:
                        field += "!r"
                    elif conversion == 115:
                        field += "!s"
                    elif conversion != -1:
                        raise Python2CompatibilityError(
                            "unsupported f-string conversion %r" % conversion
                        )
                    if item.format_spec is not None:
                        field += ":" + render_joined(item.format_spec)
                    pieces.append(field + "}")
                else:
                    raise Python2CompatibilityError(
                        "unsupported expression in f-string: %s" % type(item).__name__
                    )
            return "".join(pieces)

        template = render_joined(node)
        if not values:
            literal = template.replace("{{", "{").replace("}}", "}")
            return ast.copy_location(ast.Constant(value=literal), node)
        call = ast.Call(
            func=ast.Name(id="_mcp_fstring", ctx=ast.Load()),
            args=[ast.Constant(value=template)] + values,
            keywords=[],
        )
        return ast.copy_location(call, node)

    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id == "str":
            node.func = ast.copy_location(ast.Name(id="_mcp_text", ctx=ast.Load()), node.func)
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "isinstance"
            and len(node.args) >= 2
        ):
            type_arg = node.args[1]
            if isinstance(type_arg, ast.Name) and type_arg.id == "str":
                node.args[1] = ast.copy_location(
                    ast.Name(id="_mcp_string_types", ctx=ast.Load()), type_arg
                )
            elif isinstance(type_arg, ast.Tuple) and any(
                isinstance(item, ast.Name) and item.id == "str" for item in type_arg.elts
            ):
                other_types = [
                    item for item in type_arg.elts
                    if not (isinstance(item, ast.Name) and item.id == "str")
                ]
                node.args[1] = ast.copy_location(
                    ast.BinOp(
                        left=ast.Name(id="_mcp_string_types", ctx=ast.Load()),
                        op=ast.Add(),
                        right=ast.Tuple(elts=other_types, ctx=ast.Load()),
                    ),
                    type_arg,
                )
        return node

    def visit_Attribute(self, node):
        self.generic_visit(node)
        if (
            isinstance(node.value, ast.Name)
            and node.value.id == "json"
            and node.attr == "JSONDecodeError"
        ):
            return ast.copy_location(ast.Name(id="ValueError", ctx=ast.Load()), node)
        return node


def _prefix_python2_unicode_literals(source, filename):
    """Make Python 3 string literals explicit unicode in Python 2 source."""
    converted = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.STRING:
            literal = token.string
            prefix_end = 0
            while prefix_end < len(literal) and literal[prefix_end].lower() in "rubf":
                prefix_end += 1
            prefix = literal[:prefix_end].lower()
            if "f" in prefix:
                raise Python2CompatibilityError(
                    "%s left an f-string unconverted at line %s"
                    % (filename, token.start[0])
                )
            if "b" not in prefix and "u" not in prefix:
                token = token._replace(string="u" + literal)
        converted.append(token)
    return tokenize.untokenize(converted)


def _validate_python2_subset(tree, filename):
    unsupported = []
    py3_only = tuple(
        item for item in (
            getattr(ast, "AsyncFunctionDef", None),
            getattr(ast, "AsyncFor", None),
            getattr(ast, "AsyncWith", None),
            getattr(ast, "Await", None),
            getattr(ast, "NamedExpr", None),
            getattr(ast, "Nonlocal", None),
            getattr(ast, "YieldFrom", None),
            getattr(ast, "Match", None),
            getattr(ast, "TryStar", None),
            getattr(ast, "MatMult", None),
        ) if item is not None
    )
    call_starred_args = {
        id(argument)
        for call in ast.walk(tree)
        if isinstance(call, ast.Call)
        for argument in call.args
        if isinstance(argument, ast.Starred)
    }
    type_alias = getattr(ast, "TypeAlias", None)
    for node in ast.walk(tree):
        if isinstance(node, py3_only):
            unsupported.append("%s at line %s" % (type(node).__name__, getattr(node, "lineno", "?")))
        if isinstance(node, ast.arguments):
            if getattr(node, "posonlyargs", []):
                unsupported.append("positional-only arguments at line %s" % getattr(node, "lineno", "?"))
            if getattr(node, "kwonlyargs", []):
                unsupported.append("keyword-only arguments at line %s" % getattr(node, "lineno", "?"))
        if type_alias is not None and isinstance(node, type_alias):
            unsupported.append("type aliases are not supported at line %s" % getattr(node, "lineno", "?"))
        if getattr(node, "type_params", []):
            unsupported.append("type parameters at line %s" % getattr(node, "lineno", "?"))
        if isinstance(node, ast.Raise) and getattr(node, "cause", None) is not None:
            unsupported.append("raise-from at line %s" % getattr(node, "lineno", "?"))
        if isinstance(node, ast.Dict) and any(key is None for key in node.keys):
            unsupported.append("dictionary unpacking at line %s" % getattr(node, "lineno", "?"))
        if isinstance(node, ast.Starred):
            if isinstance(node.ctx, ast.Store):
                unsupported.append("extended iterable unpacking at line %s" % getattr(node, "lineno", "?"))
            elif id(node) not in call_starred_args:
                unsupported.append("container unpacking at line %s" % getattr(node, "lineno", "?"))
    if unsupported:
        raise Python2CompatibilityError(
            "%s contains syntax unsupported by Max 2020 Python 2.7: %s"
            % (filename, ", ".join(sorted(set(unsupported))))
        )


def transpile_python2_source(source, filename="<3dsMaxMCP tool>"):
    """Return UTF-8 Python 2.7-compatible source for the supported tool subset."""
    if isinstance(source, bytes):
        source = source.decode("utf-8")
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as exc:
        raise Python2CompatibilityError(
            "%s could not be parsed for Max 2020 compatibility: %s"
            % (filename, exc)
        ) from exc
    _validate_python2_subset(tree, filename)
    tree = _Python2Transformer().visit(tree)
    ast.fix_missing_locations(tree)
    body = ast.unparse(tree)
    body = _prefix_python2_unicode_literals(body, filename)
    return "# -*- coding: utf-8 -*-\n" + body + "\n"


def transpile_user_python2_source(source, filename="<execute_python_script>"):
    """Convert modern script syntax when possible; preserve Python 2-only source."""
    try:
        ast.parse(source, filename=filename)
    except SyntaxError:
        return source
    return transpile_python2_source(source, filename)
