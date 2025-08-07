from pycparser import c_parser, c_ast, plyparser

class CtoPythonTranspiler(c_ast.NodeVisitor):
    def __init__(self):
        self.lines = []
        self.indent_level = 0
        self.switch_var = None
        self.case_seen = False

    def indent(self):
        return '    ' * self.indent_level

    def visit_FileAST(self, node):
        for ext in node.ext:
            self.visit(ext)

    def visit_FuncDef(self, node):
        func_name = node.decl.name
        args = self._get_func_args(node.decl.type.args)
        self.lines.append(f"{self.indent()}def {func_name}({args}):")
        self.indent_level += 1
        self.visit(node.body)
        self.indent_level -= 1

    def _get_func_args(self, args):
        if not args:
            return ""
        return ", ".join([param.name for param in args.params])

    def visit_Compound(self, node):
        for stmt in node.block_items or []:
            code = self.visit(stmt)
            if code:
                if isinstance(code, list):
                    for line in code:
                        self.lines.append(f"{self.indent()}{line}")
                else:
                    self.lines.append(f"{self.indent()}{code}")

    def visit_Decl(self, node):
        if isinstance(node.type, c_ast.TypeDecl):
            name = node.name
            value = self.visit(node.init) if node.init else "None"
            return f"{name} = {value}"
        elif isinstance(node.type, c_ast.ArrayDecl):
            name = node.name
            size = self.visit(node.type.dim)
            return f"{name} = [None] * {size}"
        return ""

    def visit_Assignment(self, node):
        left = self.visit(node.lvalue)
        right = self.visit(node.rvalue)
        return f"{left} = {right}"

    def visit_Return(self, node):
        value = self.visit(node.expr)
        return f"return {value}"

    def visit_If(self, node):
        cond = self.visit(node.cond)
        self.lines.append(f"{self.indent()}if {cond}:")
        self.indent_level += 1
        self.visit(node.iftrue)
        self.indent_level -= 1
        if node.iffalse:
            self.lines.append(f"{self.indent()}else:")
            self.indent_level += 1
            self.visit(node.iffalse)
            self.indent_level -= 1

    def visit_While(self, node):
        cond = self.visit(node.cond)
        self.lines.append(f"{self.indent()}while {cond}:")
        self.indent_level += 1
        self.visit(node.stmt)
        self.indent_level -= 1

    def visit_For(self, node):
        var_name = self.visit(node.init.lvalue)
        start_val = self.visit(node.init.rvalue)
        end_val = self.visit(node.cond.right)
        self.lines.append(f"{self.indent()}for {var_name} in range({start_val}, {end_val}):")
        self.indent_level += 1
        self.visit(node.stmt)
        self.indent_level -= 1

    def visit_ArrayRef(self, node):
        name = self.visit(node.name)
        subscript = self.visit(node.subscript)
        return f"{name}[{subscript}]"

    def visit_Switch(self, node):
        var = self.visit(node.cond)
        self.lines.append(f"{self.indent()}# switch({var}) equivalent")
        self.switch_var = var
        self.case_seen = False
        self.visit(node.stmt)
        self.switch_var = None

    def visit_Case(self, node):
        val = self.visit(node.expr)
        prefix = "if" if not self.case_seen else "elif"
        self.lines.append(f"{self.indent()}{prefix} {self.switch_var} == {val}:")
        self.case_seen = True
        self.indent_level += 1
        for stmt in node.stmts:
            code = self.visit(stmt)
            if code:
                if isinstance(code, list):
                    for line in code:
                        self.lines.append(f"{self.indent()}{line}")
                else:
                    self.lines.append(f"{self.indent()}{code}")
        self.indent_level -= 1

    def visit_Default(self, node):
        self.lines.append(f"{self.indent()}else:")
        self.indent_level += 1
        for stmt in node.stmts:
            code = self.visit(stmt)
            if code:
                self.lines.append(f"{self.indent()}{code}")
        self.indent_level -= 1

    def visit_FuncCall(self, node):
        func_name = self.visit(node.name)
        args = ", ".join([self.visit(arg) for arg in node.args.exprs]) if node.args else ""
        if func_name == "printf":
            return f"print({args})"
        return f"{func_name}({args})"

    def visit_ID(self, node):
        return node.name

    def visit_Constant(self, node):
        return node.value

    def visit_BinaryOp(self, node):
        left = self.visit(node.left)
        op = node.op
        right = self.visit(node.right)
        return f"{left} {op} {right}"

    def visit_UnaryOp(self, node):
        expr = self.visit(node.expr)
        return f"{node.op}{expr}"

    def generic_visit(self, node):
        return f"# [Unhandled: {type(node).__name__}]"

def convert_c_to_python(c_code: str) -> str:
    # Remove preprocessor lines like #include
    c_code = '\n'.join(line for line in c_code.splitlines() if not line.strip().startswith('#'))
    try:
        parser = c_parser.CParser()
        ast = parser.parse(c_code)
        transpiler = CtoPythonTranspiler()
        transpiler.visit(ast)
        return "\n".join(transpiler.lines)
    except plyparser.ParseError as e:
        return f"# Error: Could not parse C code.\n# Details: {e}"
