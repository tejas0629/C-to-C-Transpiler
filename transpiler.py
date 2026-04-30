import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


KEYWORDS = {
    "int", "float", "double", "char", "void", "if", "else", "for", "while",
    "return", "break", "continue", "printf", "scanf", "public", "class",
    "static", "def", "import", "from", "as", "with", "try", "except",
}

TOKEN_SPECIFICATION = [
    ("PREPROCESSOR", r"#[^\n]*"),
    ("COMMENT", r"//.*?$|/\*.*?\*/"),
    ("STRING", r'"([^"\\]|\\.)*"'),
    ("NUMBER", r"\d+(?:\.\d+)?"),
    ("ID", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("OP", r"::==|!=|<=|>=|\+\+|--|&&|\|\||::|[+\-*/%=<>!&|]"),
    ("PUNCT", r"[{}()\[\],;]"),
    ("NEWLINE", r"\n"),
    ("SKIP", r"[ \t\r]+"),
    ("MISMATCH", r"."),
]

MASTER_PATTERN = re.compile(
    "|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPECIFICATION),
    re.MULTILINE | re.DOTALL,
)


@dataclass
class Token:
    token_type: str
    lexeme: str
    line: int
    column: int


@dataclass
class CompilerResult:
    phases: Dict[str, Any]
    translated_code: str
    parse_tree: Dict[str, Any]
    source_lang: str
    target_lang: str


class ParseError(Exception):
    pass


class ExpressionParser:
    def __init__(self, expr_tokens: List[Token]):
        self.tokens = [tok for tok in expr_tokens if tok.token_type != "SKIP"]
        self.index = 0

    def parse(self) -> Dict[str, Any]:
        if not self.tokens:
            return {"type": "EmptyExpr", "value": ""}
        node = self._parse_logical_or()
        return node

    def _peek(self) -> Optional[Token]:
        if self.index < len(self.tokens):
            return self.tokens[self.index]
        return None

    def _advance(self) -> Optional[Token]:
        tok = self._peek()
        if tok is not None:
            self.index += 1
        return tok

    def _match(self, lexemes: Tuple[str, ...]) -> Optional[Token]:
        tok = self._peek()
        if tok and tok.lexeme in lexemes:
            self.index += 1
            return tok
        return None

    def _parse_logical_or(self) -> Dict[str, Any]:
        node = self._parse_logical_and()
        while self._match(("||",)):
            operator = self.tokens[self.index - 1].lexeme
            right = self._parse_logical_and()
            node = {"type": "BinaryExpr", "operator": operator, "left": node, "right": right}
        return node

    def _parse_logical_and(self) -> Dict[str, Any]:
        node = self._parse_equality()
        while self._match(("&&",)):
            operator = self.tokens[self.index - 1].lexeme
            right = self._parse_equality()
            node = {"type": "BinaryExpr", "operator": operator, "left": node, "right": right}
        return node

    def _parse_equality(self) -> Dict[str, Any]:
        node = self._parse_comparison()
        while self._match(("==", "!=")):
            operator = self.tokens[self.index - 1].lexeme
            right = self._parse_comparison()
            node = {"type": "BinaryExpr", "operator": operator, "left": node, "right": right}
        return node

    def _parse_comparison(self) -> Dict[str, Any]:
        node = self._parse_term()
        while self._match(("<", ">", "<=", ">=")):
            operator = self.tokens[self.index - 1].lexeme
            right = self._parse_term()
            node = {"type": "BinaryExpr", "operator": operator, "left": node, "right": right}
        return node

    def _parse_term(self) -> Dict[str, Any]:
        node = self._parse_factor()
        while self._match(("+", "-")):
            operator = self.tokens[self.index - 1].lexeme
            right = self._parse_factor()
            node = {"type": "BinaryExpr", "operator": operator, "left": node, "right": right}
        return node

    def _parse_factor(self) -> Dict[str, Any]:
        node = self._parse_unary()
        while self._match(("*", "/", "%")):
            operator = self.tokens[self.index - 1].lexeme
            right = self._parse_unary()
            node = {"type": "BinaryExpr", "operator": operator, "left": node, "right": right}
        return node

    def _parse_unary(self) -> Dict[str, Any]:
        if self._match(("!", "-", "++", "--")):
            operator = self.tokens[self.index - 1].lexeme
            operand = self._parse_unary()
            return {"type": "UnaryExpr", "operator": operator, "operand": operand}
        return self._parse_primary()

    def _parse_primary(self) -> Dict[str, Any]:
        tok = self._advance()
        if not tok:
            return {"type": "Unknown", "value": ""}
        if tok.lexeme == "(":
            node = self._parse_logical_or()
            if self._peek() and self._peek().lexeme == ")":
                self._advance()
            return node
        if tok.token_type == "NUMBER":
            return {"type": "NumberLiteral", "value": tok.lexeme}
        if tok.token_type == "STRING":
            return {"type": "StringLiteral", "value": tok.lexeme}
        if tok.token_type == "ID":
            if self._peek() and self._peek().lexeme == "(":
                self._advance()
                args = []
                arg_tokens: List[Token] = []
                paren_depth = 1
                while self._peek() is not None and paren_depth > 0:
                    nxt = self._advance()
                    if nxt.lexeme == "(":
                        paren_depth += 1
                        arg_tokens.append(nxt)
                    elif nxt.lexeme == ")":
                        paren_depth -= 1
                        if paren_depth == 0:
                            break
                        arg_tokens.append(nxt)
                    elif nxt.lexeme == "," and paren_depth == 1:
                        args.append(ExpressionParser(arg_tokens).parse())
                        arg_tokens = []
                    else:
                        arg_tokens.append(nxt)
                if arg_tokens:
                    args.append(ExpressionParser(arg_tokens).parse())
                return {"type": "CallExpr", "callee": tok.lexeme, "arguments": args}
            return {"type": "Identifier", "name": tok.lexeme}
        return {"type": "Unknown", "value": tok.lexeme}


class SimpleCParser:
    def __init__(self, tokens: List[Token]):
        self.tokens = [
            t for t in tokens if t.token_type not in {"COMMENT", "NEWLINE", "SKIP", "PREPROCESSOR"}
        ]
        self.position = 0

    def parse(self) -> Dict[str, Any]:
        root = {"type": "Program", "children": []}
        while not self._at_end():
            root["children"].append(self._parse_declaration_or_statement())
        return root

    def _peek(self) -> Token:
        return self.tokens[self.position]

    def _previous(self) -> Token:
        return self.tokens[self.position - 1]

    def _at_end(self) -> bool:
        return self.position >= len(self.tokens)

    def _advance(self) -> Token:
        if not self._at_end():
            self.position += 1
        return self._previous()

    def _check(self, lexeme: str) -> bool:
        return not self._at_end() and self._peek().lexeme == lexeme

    def _check_type(self, token_type: str) -> bool:
        return not self._at_end() and self._peek().token_type == token_type

    def _consume(self, lexeme: str, message: str) -> Token:
        if self._check(lexeme):
            return self._advance()
        raise ParseError(message)

    def _parse_declaration_or_statement(self) -> Dict[str, Any]:
        if self._check_type("KEYWORD") and self._peek().lexeme in {"int", "float", "double", "char", "void"}:
            return self._parse_declaration()
        return self._parse_statement()

    def _parse_declaration(self) -> Dict[str, Any]:
        vartype = self._advance().lexeme
        if not self._check_type("ID"):
            raise ParseError("Expected identifier in declaration")
        name = self._advance().lexeme

        if self._check("("):
            return self._parse_function(vartype, name)

        initializer = None
        if self._check("="):
            self._advance()
            expr_tokens = self._collect_until((";",))
            initializer = ExpressionParser(expr_tokens).parse()
        self._consume(";", "Expected ';' after declaration")
        return {"type": "VarDecl", "varType": vartype, "name": name, "initializer": initializer}

    def _parse_function(self, return_type: str, name: str) -> Dict[str, Any]:
        self._consume("(", "Expected '(' for function declaration")
        params = []
        while not self._check(")"):
            ptype = self._advance().lexeme
            pname = self._advance().lexeme
            params.append({"type": ptype, "name": pname})
            if self._check(","):
                self._advance()
        self._consume(")", "Expected ')' after parameters")
        body = self._parse_block()
        return {"type": "FunctionDecl", "returnType": return_type, "name": name, "params": params, "body": body}

    def _parse_block(self) -> Dict[str, Any]:
        self._consume("{", "Expected '{' at start of block")
        statements = []
        while not self._check("}") and not self._at_end():
            statements.append(self._parse_declaration_or_statement())
        self._consume("}", "Expected '}' at end of block")
        return {"type": "Block", "children": statements}

    def _parse_statement(self) -> Dict[str, Any]:
        if self._check("{"):
            return self._parse_block()
        if self._check("if"):
            return self._parse_if()
        if self._check("while"):
            return self._parse_while()
        if self._check("for"):
            return self._parse_for()
        if self._check("return"):
            self._advance()
            expr_tokens = self._collect_until((";",))
            self._consume(";", "Expected ';' after return")
            return {"type": "ReturnStmt", "value": ExpressionParser(expr_tokens).parse() if expr_tokens else None}

        expr_tokens = self._collect_until((";",))
        self._consume(";", "Expected ';' after expression")
        return {"type": "ExprStmt", "expression": ExpressionParser(expr_tokens).parse()}

    def _parse_if(self) -> Dict[str, Any]:
        self._consume("if", "Expected 'if'")
        self._consume("(", "Expected '(' after if")
        condition_tokens = self._collect_until((")",))
        self._consume(")", "Expected ')' after if condition")
        then_branch = self._parse_statement()
        else_branch = None
        if self._check("else"):
            self._advance()
            else_branch = self._parse_statement()
        return {
            "type": "IfStmt",
            "condition": ExpressionParser(condition_tokens).parse(),
            "then": then_branch,
            "else": else_branch,
        }

    def _parse_while(self) -> Dict[str, Any]:
        self._consume("while", "Expected 'while'")
        self._consume("(", "Expected '(' after while")
        condition_tokens = self._collect_until((")",))
        self._consume(")", "Expected ')' after while condition")
        body = self._parse_statement()
        return {"type": "WhileStmt", "condition": ExpressionParser(condition_tokens).parse(), "body": body}

    def _parse_for(self) -> Dict[str, Any]:
        self._consume("for", "Expected 'for'")
        self._consume("(", "Expected '(' after for")
        init_tokens = self._collect_until((";",))
        self._consume(";", "Expected ';' in for init")
        cond_tokens = self._collect_until((";",))
        self._consume(";", "Expected ';' in for condition")
        step_tokens = self._collect_until((")",))
        self._consume(")", "Expected ')' after for clauses")
        body = self._parse_statement()
        return {
            "type": "ForStmt",
            "init": ExpressionParser(init_tokens).parse() if init_tokens else None,
            "condition": ExpressionParser(cond_tokens).parse() if cond_tokens else None,
            "step": ExpressionParser(step_tokens).parse() if step_tokens else None,
            "body": body,
        }

    def _collect_until(self, stop_lexemes: Tuple[str, ...]) -> List[Token]:
        collected = []
        depth = 0
        while not self._at_end():
            tok = self._peek()
            if tok.lexeme == "(":
                depth += 1
            elif tok.lexeme == ")":
                if depth == 0 and ")" in stop_lexemes:
                    break
                depth = max(depth - 1, 0)

            if depth == 0 and tok.lexeme in stop_lexemes:
                break
            collected.append(self._advance())
        return collected


def lexical_analysis(code: str) -> List[Token]:
    tokens = []
    line_number = 1
    line_start = 0

    for match in MASTER_PATTERN.finditer(code):
        token_type = match.lastgroup
        lexeme = match.group()
        column = match.start() - line_start + 1

        if token_type == "NEWLINE":
            line_number += 1
            line_start = match.end()
            tokens.append(Token(token_type, lexeme, line_number - 1, column))
            continue

        if token_type == "ID" and lexeme in KEYWORDS:
            token_type = "KEYWORD"

        if token_type == "MISMATCH":
            raise ParseError(f"Unexpected character {lexeme!r} at line {line_number}, column {column}")

        tokens.append(Token(token_type, lexeme, line_number, column))

    return tokens


def syntactic_analysis(tokens: List[Token]) -> Dict[str, Any]:
    parser = SimpleCParser(tokens)
    return parser.parse()


def semantic_analysis(parse_tree: Dict[str, Any]) -> List[str]:
    symbols: Dict[str, str] = {}
    diagnostics: List[str] = []

    def walk(node: Dict[str, Any]):
        ntype = node.get("type")
        if ntype == "VarDecl":
            name = node.get("name")
            var_type = node.get("varType")
            if name in symbols:
                diagnostics.append(f"Variable '{name}' redeclared.")
            symbols[name] = var_type
        elif ntype == "FunctionDecl":
            fname = node.get("name")
            symbols[fname] = f"function<{node.get('returnType')}>"
            for param in node.get("params", []):
                pname = param.get("name")
                symbols[pname] = param.get("type")
            walk(node.get("body", {}))
        elif ntype == "Block":
            for child in node.get("children", []):
                walk(child)
        elif ntype in {"IfStmt", "WhileStmt", "ForStmt"}:
            for key in ("then", "else", "body"):
                branch = node.get(key)
                if isinstance(branch, dict):
                    walk(branch)
        elif ntype == "Program":
            for child in node.get("children", []):
                walk(child)

    walk(parse_tree)
    if not diagnostics:
        diagnostics.append("Semantic analysis completed: no redeclaration errors detected.")
    return diagnostics


def intermediate_code_generation(tokens: List[Token]) -> List[str]:
    source = " ".join(
        tok.lexeme for tok in tokens if tok.token_type not in {"COMMENT", "NEWLINE", "SKIP", "PREPROCESSOR"}
    )
    tac = []
    for idx, statement in enumerate(source.split(";"), start=1):
        statement = statement.strip()
        if statement:
            tac.append(f"t{idx} := {statement}")
    return tac[:40]


def optimize_intermediate_code(ir: List[str]) -> List[str]:
    optimized = []
    for line in ir:
        collapsed = re.sub(r"\s+", " ", line).strip()
        collapsed = collapsed.replace(" + 0", "")
        collapsed = collapsed.replace(" * 1", "")
        optimized.append(collapsed)
    return optimized


class Translator(ABC):
    """Base class for all language translators."""

    @abstractmethod
    def translate(self, code: str) -> str:
        pass

    @abstractmethod
    def get_source_lang(self) -> str:
        pass

    @abstractmethod
    def get_target_lang(self) -> str:
        pass


class CToC_Translator(Translator):
    """C to C++ Translator."""

    def get_source_lang(self) -> str:
        return "C"

    def get_target_lang(self) -> str:
        return "C++"

    def translate(self, code: str) -> str:
        cpp = code

        cpp = re.sub(r"#include\s*<stdio\.h>", "#include <iostream>", cpp)
        if "#include <iostream>" not in cpp:
            cpp = "#include <iostream>\n" + cpp

        if "using namespace std;" not in cpp:
            cpp = cpp.replace("#include <iostream>", "#include <iostream>\nusing namespace std;")

        cpp = re.sub(r"\bprintf\s*\((.*?)\)\s*;", self._convert_printf_call, cpp, flags=re.DOTALL)
        cpp = re.sub(r"\bscanf\s*\((.*?)\)\s*;", self._convert_scanf_call, cpp, flags=re.DOTALL)

        cpp = re.sub(r"\bmalloc\s*\(", "new ", cpp)
        cpp = re.sub(r"\bfree\s*\(", "delete ", cpp)

        return cpp

    def _convert_printf_call(self, match: re.Match) -> str:
        inside = match.group(1)
        arguments = self._split_arguments(inside)
        if not arguments:
            return "std::cout << std::endl;"

        first = arguments[0]
        if not first.startswith('"'):
            return f"std::cout << {inside} << std::endl;"

        fmt = first.strip('"')
        values = arguments[1:]
        parts = re.split(r"(%[dfscl])", fmt)
        converted_parts: List[str] = []
        value_index = 0

        for part in parts:
            if re.fullmatch(r"%[dfscl]", part):
                if value_index < len(values):
                    converted_parts.append(values[value_index])
                value_index += 1
            elif part:
                converted_parts.append(repr(part).replace("'", '"'))

        stream = " << ".join(converted_parts) if converted_parts else '""'
        return f"std::cout << {stream} << std::endl;"

    def _convert_scanf_call(self, match: re.Match) -> str:
        inside = match.group(1)
        arguments = self._split_arguments(inside)
        values = [arg.replace("&", "").strip() for arg in arguments[1:]]
        if not values:
            return "// TODO: scanf conversion requires variable references"
        return "std::cin >> " + " >> ".join(values) + ";"

    def _split_arguments(self, arg_text: str) -> List[str]:
        if not arg_text.strip():
            return []
        args = []
        current = []
        depth = 0
        in_string = False
        escaped = False

        for char in arg_text:
            if in_string:
                current.append(char)
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
                current.append(char)
            elif char == "(":
                depth += 1
                current.append(char)
            elif char == ")":
                depth -= 1
                current.append(char)
            elif char == "," and depth == 0:
                args.append("".join(current).strip())
                current = []
            else:
                current.append(char)

        if current:
            args.append("".join(current).strip())
        return args


class CppToCTranslator(Translator):
    """C++ to C Translator."""

    def get_source_lang(self) -> str:
        return "C++"

    def get_target_lang(self) -> str:
        return "C"

    def translate(self, code: str) -> str:
        c_code = code

        # Remove scope resolution operators
        c_code = re.sub(r"std::", "", c_code)
        
        # Replace includes
        c_code = re.sub(r"#include\s*<iostream>", "#include <stdio.h>", c_code)
        c_code = re.sub(r"using\s+namespace\s+std\s*;", "", c_code)

        # Convert cout to printf - handle multiple << operators
        def convert_cout_line(match):
            full_expr = match.group(1)
            # Remove extra << and endl
            parts = [p.strip() for p in full_expr.split("<<")]
            if parts[-1] == "endl":
                parts = parts[:-1]
            
            # Build printf format string
            printf_args = []
            format_str = ""
            for part in parts:
                if part.startswith('"') and part.endswith('"'):
                    format_str += part.strip('"')
                else:
                    format_str += "%s"
                    printf_args.append(part)
            
            if printf_args:
                return f'printf("{format_str}\\n", {", ".join(printf_args)});'
            else:
                return f'printf("{format_str}\\n");'
        
        c_code = re.sub(r"cout\s*<<\s*(.*?)\s*;", convert_cout_line, c_code, flags=re.DOTALL)
        
        # Convert cin to scanf
        c_code = re.sub(r"cin\s*>>\s*(.*?)\s*;", 
                       lambda m: f"scanf(\"%d\", &{m.group(1).strip()});", c_code)

        # Convert memory management
        c_code = re.sub(r"\bnew\s+(\w+)", r"malloc(sizeof(\1))", c_code)
        c_code = re.sub(r"\bdelete\s+", "free(", c_code)

        return c_code

    def _convert_cout_to_printf(self, output_expr: str) -> str:
        output_expr = output_expr.strip()
        if '"' in output_expr:
            return f'printf("{output_expr}\\n");'
        return f'printf("%d\\n", {output_expr});'


class CToJavaTranslator(Translator):
    """C to Java Translator."""

    def get_source_lang(self) -> str:
        return "C"

    def get_target_lang(self) -> str:
        return "Java"

    def translate(self, code: str) -> str:
        java = "public class Program {\n    public static void main(String[] args) {\n"

        lines = code.split("\n")
        for line in lines:
            if re.match(r"#include", line) or re.match(r"int main", line) or ("main" in code and "{" in line):
                continue
            if line.strip().startswith("return"):
                continue

            java_line = self._convert_c_statement_to_java(line)
            if java_line.strip():
                java += "        " + java_line + "\n"

        java += "    }\n}\n"
        return java

    def _convert_c_statement_to_java(self, statement: str) -> str:
        statement = statement.strip()

        statement = re.sub(r"\bint\s+(\w+)", r"int \1", statement)
        statement = re.sub(r"\bfloat\s+(\w+)", r"float \1", statement)
        statement = re.sub(r"\bchar\s+(\w+)", r"char \1", statement)

        statement = re.sub(r"\bprintf\s*\((.*?)\)\s*;", lambda m: self._convert_c_printf_to_java(m.group(1)), statement, flags=re.DOTALL)
        statement = re.sub(r"\bscanf\s*\((.*?)\)\s*;", "// TODO: Convert scanf", statement, flags=re.DOTALL)

        return statement

    def _convert_c_printf_to_java(self, args_str: str) -> str:
        args_str = args_str.strip()
        if args_str.startswith('"'):
            return f'System.out.println({args_str});'
        return f'System.out.println({args_str});'


class JavaToCTranslator(Translator):
    """Java to C Translator."""

    def get_source_lang(self) -> str:
        return "Java"

    def get_target_lang(self) -> str:
        return "C"

    def translate(self, code: str) -> str:
        c_code = "#include <stdio.h>\n\nint main() {\n"

        lines = code.split("\n")
        for line in lines:
            if "public class" in line or "public static void main" in line or "{" in line or "}" in line:
                continue
            if "System.out.println" in line:
                c_code += "    printf(\"" + line.split("println(")[1].rstrip(");") + "\\n\");\n"
            elif line.strip() and not line.strip().startswith("//"):
                c_code += "    " + line.strip() + "\n"

        c_code += "    return 0;\n}\n"
        return c_code


class CToPythonTranslator(Translator):
    """C to Python Translator."""

    def get_source_lang(self) -> str:
        return "C"

    def get_target_lang(self) -> str:
        return "Python"

    def translate(self, code: str) -> str:
        python = ""

        lines = code.split("\n")
        for line in lines:
            if re.match(r"#include", line):
                continue
            if re.match(r"int main", line):
                continue

            if "{" in line and "main" not in line:
                continue
            if line.strip() == "}":
                continue

            python_line = self._convert_c_statement_to_python(line)
            if python_line.strip():
                python += python_line + "\n"

        return python

    def _convert_c_statement_to_python(self, statement: str) -> str:
        statement = statement.strip()

        statement = re.sub(r"\bint\s+(\w+)\s*=", r"\1 =", statement)
        statement = re.sub(r"\bfloat\s+(\w+)\s*=", r"\1 =", statement)
        statement = re.sub(r"\bchar\s+(\w+)\s*=", r"\1 =", statement)
        statement = re.sub(r";\s*$", "", statement)

        statement = re.sub(r"\bprintf\s*\((.*?)\)\s*;?", lambda m: self._convert_c_printf_to_python(m.group(1)), statement, flags=re.DOTALL)

        return statement

    def _convert_c_printf_to_python(self, args_str: str) -> str:
        args_str = args_str.strip()
        return f"print({args_str})"


class PythonToCTranslator(Translator):
    """Python to C Translator."""

    def get_source_lang(self) -> str:
        return "Python"

    def get_target_lang(self) -> str:
        return "C"

    def translate(self, code: str) -> str:
        c_code = "#include <stdio.h>\n\nint main() {\n"

        lines = code.split("\n")

        for line in lines:
            stripped = line.lstrip()
            if not stripped or stripped.startswith("#"):
                continue

            if "print(" in line:
                print_match = re.search(r"print\((.*)\)", line)
                if print_match:
                    content = print_match.group(1)
                    c_code += "    printf(\"%s\\n\", " + content + ");\n"
            elif "=" in line and "==" not in line:
                parts = line.split("=")
                if len(parts) == 2:
                    var_name = parts[0].strip()
                    var_value = parts[1].strip()
                    c_code += f"    int {var_name} = {var_value};\n"
            elif stripped.startswith("if"):
                condition = stripped.replace("if ", "").rstrip(":")
                c_code += f"    if ({condition}) {{\n"
            elif stripped.startswith("while"):
                condition = stripped.replace("while ", "").rstrip(":")
                c_code += f"    while ({condition}) {{\n"

        c_code += "    return 0;\n}\n"
        return c_code


class CppToJavaTranslator(Translator):
    """C++ to Java Translator."""

    def get_source_lang(self) -> str:
        return "C++"

    def get_target_lang(self) -> str:
        return "Java"

    def translate(self, code: str) -> str:
        cpp_to_c = CppToCTranslator()
        c_to_java = CToJavaTranslator()
        c_code = cpp_to_c.translate(code)
        return c_to_java.translate(c_code)


class JavaToCppTranslator(Translator):
    """Java to C++ Translator."""

    def get_source_lang(self) -> str:
        return "Java"

    def get_target_lang(self) -> str:
        return "C++"

    def translate(self, code: str) -> str:
        java_to_c = JavaToCTranslator()
        c_to_cpp = CToC_Translator()
        c_code = java_to_c.translate(code)
        return c_to_cpp.translate(c_code)


class CppToPythonTranslator(Translator):
    """C++ to Python Translator."""

    def get_source_lang(self) -> str:
        return "C++"

    def get_target_lang(self) -> str:
        return "Python"

    def translate(self, code: str) -> str:
        cpp_to_c = CppToCTranslator()
        c_to_python = CToPythonTranslator()
        c_code = cpp_to_c.translate(code)
        return c_to_python.translate(c_code)


class PythonToCppTranslator(Translator):
    """Python to C++ Translator."""

    def get_source_lang(self) -> str:
        return "Python"

    def get_target_lang(self) -> str:
        return "C++"

    def translate(self, code: str) -> str:
        python_to_c = PythonToCTranslator()
        c_to_cpp = CToC_Translator()
        c_code = python_to_c.translate(code)
        return c_to_cpp.translate(c_code)


class JavaToPythonTranslator(Translator):
    """Java to Python Translator."""

    def get_source_lang(self) -> str:
        return "Java"

    def get_target_lang(self) -> str:
        return "Python"

    def translate(self, code: str) -> str:
        java_to_c = JavaToCTranslator()
        c_to_python = CToPythonTranslator()
        c_code = java_to_c.translate(code)
        return c_to_python.translate(c_code)


class PythonToJavaTranslator(Translator):
    """Python to Java Translator."""

    def get_source_lang(self) -> str:
        return "Python"

    def get_target_lang(self) -> str:
        return "Java"

    def translate(self, code: str) -> str:
        python_to_c = PythonToCTranslator()
        c_to_java = CToJavaTranslator()
        c_code = python_to_c.translate(code)
        return c_to_java.translate(c_code)


TRANSLATORS = {
    ("C", "C++"): CToC_Translator(),
    ("C++", "C"): CppToCTranslator(),
    ("C", "Java"): CToJavaTranslator(),
    ("Java", "C"): JavaToCTranslator(),
    ("C", "Python"): CToPythonTranslator(),
    ("Python", "C"): PythonToCTranslator(),
    ("C++", "Java"): CppToJavaTranslator(),
    ("Java", "C++"): JavaToCppTranslator(),
    ("C++", "Python"): CppToPythonTranslator(),
    ("Python", "C++"): PythonToCppTranslator(),
    ("Java", "Python"): JavaToPythonTranslator(),
    ("Python", "Java"): PythonToJavaTranslator(),
}


def get_translator(source_lang: str, target_lang: str) -> Optional[Translator]:
    """Get translator for given language pair."""
    return TRANSLATORS.get((source_lang, target_lang))


def transpile_with_phases(code: str, source_lang: str = "C", target_lang: str = "C++") -> CompilerResult:
    """Transpile code from source language to target language."""

    if source_lang == target_lang:
        raise ParseError("Source and target languages must be different.")

    translator = get_translator(source_lang, target_lang)
    if not translator:
        raise ParseError(f"Translation from {source_lang} to {target_lang} is not supported.")

    if not code.strip():
        raise ParseError("Please provide source code before transpiling.")

    # Initialize default values for phases
    tokens = []
    parse_tree = {"type": "Program", "children": []}
    semantic_notes = []
    intermediate = []
    optimized_ir = []
    translated_code = ""
    error_msg = None

    try:
        # Try to perform all compilation phases
        try:
            tokens = lexical_analysis(code)
        except ParseError as e:
            error_msg = f"Lexical Analysis Warning: {str(e)}"
            # Continue with empty tokens
            tokens = []
        
        try:
            parse_tree = syntactic_analysis(tokens) if tokens else {"type": "Program", "children": []}
        except ParseError as e:
            error_msg = error_msg or f"Syntax Analysis Warning: {str(e)}"
            # Continue with default parse tree
            parse_tree = {"type": "Program", "children": []}
        
        try:
            semantic_notes = semantic_analysis(parse_tree)
        except Exception as e:
            error_msg = error_msg or f"Semantic Analysis Warning: {str(e)}"
            semantic_notes = ["Semantic analysis skipped due to unsupported syntax."]
        
        try:
            intermediate = intermediate_code_generation(tokens) if tokens else []
        except Exception as e:
            error_msg = error_msg or f"IR Generation Warning: {str(e)}"
            intermediate = []
        
        try:
            optimized_ir = optimize_intermediate_code(intermediate) if intermediate else []
        except Exception as e:
            error_msg = error_msg or f"Optimization Warning: {str(e)}"
            optimized_ir = []
        
        # Try translation
        try:
            translated_code = translator.translate(code)
        except Exception as e:
            # Graceful fallback: return original code with warning
            translated_code = code
            error_msg = f"Translation Warning: Some syntax may not be fully supported. {str(e)}"
    
    except Exception as e:
        raise ParseError(f"Critical translation error: {str(e)}")

    # Build status message
    status_msg = f"Translation from {source_lang} to {target_lang} completed"
    if error_msg:
        status_msg += f" with warnings: {error_msg}"
    else:
        status_msg += " successfully."

    phases = {
        "1_lexical_analysis": [token.__dict__ for token in tokens] if tokens else [],
        "2_syntax_analysis": parse_tree,
        "3_semantic_analysis": semantic_notes,
        "4_intermediate_code_generation": intermediate,
        "5_code_optimization": optimized_ir,
        "6_code_generation": translated_code,
        "7_symbol_table_and_report": {
            "tokens_count": len(tokens),
            "ir_count": len(intermediate),
            "status": status_msg,
            "warnings": error_msg if error_msg else "No warnings",
        },
    }

    return CompilerResult(
        phases=phases,
        translated_code=translated_code,
        parse_tree=parse_tree,
        source_lang=source_lang,
        target_lang=target_lang,
    )
