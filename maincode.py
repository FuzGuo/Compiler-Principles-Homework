import re
import sys

# --- 1. 词法分析 (Lexer) ---

# 定义 Token 类型
TOKENS = {
    'KEYWORD': r'\b(var|integer|longint|bool|begin|end|if|then|else|while|do)\b',
    'BOOLEAN_LITERAL': r'\b(true|false)\b',
    'IDENTIFIER': r'[a-zA-Z][a-zA-Z0-9]*',
    'INTEGER_LITERAL': r'[0-9]+',
    'ASSIGN': r':=',
    'OP_ADD': r'\+',
    'OP_SUB': r'-',
    'OP_EQ': r'=',
    'OP_NEQ': r'<>',
    'OP_LT': r'<',
    'OP_LTE': r'<=',
    'OP_GT': r'>',
    'OP_GTE': r'>=',
    'SEMICOLON': r';',
    'COLON': r':',
    'COMMA': r',',
    'LPAREN': r'\(',
    'RPAREN': r'\)',
    'WHITESPACE': r'\s+',
    'MISMATCH': r'.',
}


token_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKENS.items())

def lexer(code):
    """将 Pascal 代码字符串分解为 Token 列表"""
    tokens = []
    line_num = 1
    line_start = 0
    for mo in re.finditer(token_regex, code, flags=re.IGNORECASE):
        kind = mo.lastgroup
        value = mo.group()
        column = mo.start() - line_start + 1

        if kind == 'WHITESPACE':
            if '\n' in value:
                line_num += value.count('\n')
                line_start = mo.end() - value.rfind('\n') - 1
            continue
        elif kind == 'MISMATCH':
            raise SyntaxError(f"错误 (行 {line_num}, 列 {column}): 非法字符 '{value}'")

        # 大小写不敏感
        if kind in ['KEYWORD', 'IDENTIFIER', 'BOOLEAN_LITERAL']:
            value = value.lower()

        tokens.append({'type': kind, 'value': value, 'line': line_num, 'col': column})

    tokens.append({'type': 'EOF', 'value': None, 'line': line_num, 'col': -1})
    return tokens

# --- 2. 语法/语义分析 与 代码生成 ---
class PascalToCppConverter:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token_index = 0
        self.current_token = self.tokens[0]
        self.symbol_table = {} # {'var_name_lower': {'type': 'pascal_type', 'cpp_type': 'c++_type'}}
        self.cpp_declarations = []
        self.cpp_body = []
        self.errors = []

    def _next_token(self):
        # 更新当前 Token 的 index
        self.current_token_index += 1
        if self.current_token_index < len(self.tokens):
            self.current_token = self.tokens[self.current_token_index]
        else:
            self.current_token = {'type': 'EOF', 'value': None, 'line': -1, 'col': -1}

    def _error(self, message):
        # 记录错误信息
        token = self.current_token
        err_msg = f"错误 (行 {token.get('line', '?')}, 列 {token.get('col', '?')}): {message}"
        if token.get('value') is not None:
            err_msg += f" (遇到: '{token['value']}')"
        elif token['type'] != 'EOF':
            err_msg += f" (遇到 Token 类型: {token['type']})"
        self.errors.append(err_msg)
        raise SyntaxError(err_msg)

    def _expect(self, token_type, expected_value=None):
        # 检查当前 Token 是否符合预期
        if self.current_token['type'] == token_type:
            if expected_value is None or self.current_token['value'] == expected_value:
                token_value = self.current_token['value']
                self._next_token()
                return token_value
            else:
                self._error(f"期望得到 '{expected_value}' 但得到了 '{self.current_token['value']}'")
        else:
            expected_desc = f"'{expected_value}'" if expected_value else f"类型 '{token_type}'"
            self._error(f"期望得到 {expected_desc} 但得到了类型 '{self.current_token['type']}'")

    def _parse_type(self):
        # 解析变量类型
        token = self.current_token
        if token['type'] == 'KEYWORD' and token['value'] in ['integer', 'longint', 'bool']:
            pascal_type = token['value']
            self._next_token()
            if pascal_type == 'integer': return pascal_type, 'int'
            elif pascal_type == 'longint': return pascal_type, 'long long'
            elif pascal_type == 'bool': return pascal_type, 'bool'
        else:
            self._error("期望得到类型关键字 (integer, longint, bool)")

    def _parse_var_declaration(self):
        # 声明部分的解析
        self._expect('KEYWORD', 'var')
        if self.current_token['type'] != 'IDENTIFIER':
            self._error("关键字 'var' 后面需要跟变量名")

        while self.current_token['type'] == 'IDENTIFIER':
            variables = [self._expect('IDENTIFIER')]
            while self.current_token['type'] == 'COMMA':
                self._next_token() # 跳过逗号
                variables.append(self._expect('IDENTIFIER'))

            self._expect('COLON') # 期望冒号
            pascal_type, cpp_type = self._parse_type()
            # 转换为 cpp 声明
            cpp_declaration_line = f"{cpp_type} "
            var_names_in_line = []
            for var_name in variables:
                if var_name in self.symbol_table:
                    self._error(f"变量 '{var_name}' 重复定义")
                if not re.match(r'^[a-zA-Z][a-zA-Z0-9]*$', var_name): 
                     self._error(f"非法变量名 '{var_name}'")
                self.symbol_table[var_name] = {'type': pascal_type, 'cpp_type': cpp_type}
                var_names_in_line.append(var_name)
            
            cpp_declaration_line += ", ".join(var_names_in_line) + ";"
            self.cpp_declarations.append(cpp_declaration_line)
            self._expect('SEMICOLON') # 期望分号

    def _parse_factor(self):
        # 解析表达式中的因子 (变量, 数字, 布尔值, 括号)
        token = self.current_token
        if token['type'] == 'IDENTIFIER':
            var_name = token['value']
            if var_name not in self.symbol_table:
                self._error(f"使用了未定义的变量 '{var_name}'")
            self._next_token()
            return var_name
        elif token['type'] == 'INTEGER_LITERAL':
            value = token['value']
            self._next_token()
            return value
        elif token['type'] == 'BOOLEAN_LITERAL':
            value = token['value'].lower() 
            self._next_token()
            return value 
        elif token['type'] == 'LPAREN':
            self._next_token()
            expr = self._parse_expression()
            self._expect('RPAREN')
            return f"({expr})"
        else:
            self._error("表达式中期望得到变量, 数字, 布尔值或带括号表达式")

    def _parse_term(self): 
        return self._parse_factor()

    def _parse_expression(self):
        # 解析表达式
        cpp_expr = self._parse_term()
        while self.current_token['type'] in ['OP_ADD', 'OP_SUB']:
            op_token = self.current_token
            self._next_token()
            right_term = self._parse_term()
            cpp_expr += f" {op_token['value']} {right_term}"
        return cpp_expr

    def _parse_condition(self):
        # 解析条件表达式
        left_expr = self._parse_expression()
        
        op_map = { '=': '==', '<>': '!=' }

        if self.current_token['type'] in ['OP_EQ', 'OP_NEQ', 'OP_LT', 'OP_LTE', 'OP_GT', 'OP_GTE']:
            op_pascal = self.current_token['value']
            op_token_type = self.current_token['type']
            self._next_token()
            right_expr = self._parse_expression()
            
            op_cpp = op_map.get(op_pascal, op_pascal) 
            return f"{left_expr} {op_cpp} {right_expr}"
        else:
            # 只有布尔变量的情况
            return left_expr


    def _parse_assignment_statement(self, indent_level=1):
        # 解析赋值语句
        var_name = self._expect('IDENTIFIER')
        if var_name not in self.symbol_table:
            self._error(f"尝试给未定义的变量 '{var_name}' 赋值")
        self._expect('ASSIGN')
        cpp_expr = self._parse_expression()
        self._expect('SEMICOLON')
        indent = "    " * indent_level
        self.cpp_body.append(f"{indent}{var_name} = {cpp_expr};")

    def _parse_body_statement(self, indent_level_for_braces):
        """解析复合语句  begin...end 块"""
        braces_indent = "    " * indent_level_for_braces # 处理缩进
        statements_inside_indent_level = indent_level_for_braces + 1

        if self.current_token['type'] == 'KEYWORD' and self.current_token['value'] == 'begin':
            self._next_token() #  BEGIN
            self.cpp_body.append(f"{braces_indent}{{")
            while not (self.current_token['type'] == 'KEYWORD' and self.current_token['value'] == 'end'):
                if self.current_token['type'] == 'EOF':
                    self._error("代码在 'begin' 块内 'end' 之前意外结束")
                self._parse_statement(statements_inside_indent_level)
            self._expect('KEYWORD', 'end') #  END

            if self.current_token['type'] == 'SEMICOLON':
                 self._next_token()
            self.cpp_body.append(f"{braces_indent}}}")
        else:
            self.cpp_body.append(f"{braces_indent}{{")
            self._parse_statement(statements_inside_indent_level) 
            self.cpp_body.append(f"{braces_indent}}}")


    def _parse_if_statement(self, indent_level=1):
        base_indent = "    " * indent_level
        self._expect('KEYWORD', 'if')
        condition_cpp = self._parse_condition()
        self.cpp_body.append(f"{base_indent}if ({condition_cpp})")
        self._expect('KEYWORD', 'then')
        self._parse_body_statement(indent_level) 

        if self.current_token['type'] == 'KEYWORD' and self.current_token['value'] == 'else':
            self._next_token() 
            self.cpp_body.append(f"{base_indent}else")
            self._parse_body_statement(indent_level) 


    def _parse_while_statement(self, indent_level=1):
        base_indent = "    " * indent_level
        self._expect('KEYWORD', 'while')
        condition_cpp = self._parse_condition()
        self.cpp_body.append(f"{base_indent}while ({condition_cpp})")
        self._expect('KEYWORD', 'do')
        self._parse_body_statement(indent_level) 

    def _parse_statement(self, indent_level=1):
        """解析单条语句"""
        if self.current_token['type'] == 'IDENTIFIER':
            self._parse_assignment_statement(indent_level)
        elif self.current_token['type'] == 'KEYWORD':
            if self.current_token['value'] == 'if':
                self._parse_if_statement(indent_level)
            elif self.current_token['value'] == 'while':
                self._parse_while_statement(indent_level)
            elif self.current_token['value'] == 'begin':
                self._parse_body_statement(indent_level)
            else:
                self._error("期望得到语句的开头 (赋值, if, while, begin, 或者其他语句关键字)")
        else:
            self._error("期望得到语句的开头 (标识符, if, while, begin)")


    def _parse_implementation_block(self):
        # 解析主程序实现块 (BEGIN...END.)
        self._expect('KEYWORD', 'begin')
        while not (self.current_token['type'] == 'KEYWORD' and self.current_token['value'] == 'end'):
            if self.current_token['type'] == 'EOF':
                self._error("代码在主程序 'begin' 后 'end' 之前意外结束")
            self._parse_statement(indent_level=1)
        self._expect('KEYWORD', 'end')
        if self.current_token['type'] == 'SEMICOLON': 
            self._next_token()

    def parse(self):
        # 执行完整的解析和转换过程
        try:
            if self.current_token['type'] == 'KEYWORD' and self.current_token['value'] == 'var':
                self._parse_var_declaration()

            self._parse_implementation_block()

            if self.current_token['type'] != 'EOF':
                if self.current_token['type'] == 'MISMATCH' and self.current_token['value'] == '.':
                    self._next_token()
                    if self.current_token['type'] != 'EOF':
                         self._error(f"在程序末尾的 '.' 之后有未预期的内容")
                elif self.current_token['type'] != 'EOF':
                    self._error(f"在 'end' 之后有未预期的内容")


            if not self.errors:
                cpp_code = "#include <iostream>\n"
                cpp_code += "#include <string>\n" 
                cpp_code += "\nusing namespace std;\n\n"
                cpp_code += "int main() {\n"

                if self.cpp_declarations:
                    cpp_code += "    // Variable declarations\n"
                    for decl in self.cpp_declarations:
                        cpp_code += f"    {decl}\n" 
                    cpp_code += "\n"

                if self.cpp_body:
                    cpp_code += "    // Implementation\n"
                    for line in self.cpp_body: 
                        cpp_code += f"{line}\n"
                    cpp_code += "\n"
                else:
                    cpp_code += "    // No implementation code\n\n"

                cpp_code += "    return 0;\n"
                cpp_code += "}\n"
                return cpp_code
            else:
                return None
        except SyntaxError:
            return None 
        except Exception as e:
            self.errors.append(f"意外内部错误: {e}")
            import traceback
            traceback.print_exc()
            return None

# --- 3. 主程序 ---
def main_convert(pascal_code):
    print("--- 输入 Pascal 代码 ---")
    print(pascal_code.strip())
    print("-" * 25)

    try:
        tokens = lexer(pascal_code)
        # print("--- Tokens ---")
        # for token in tokens:
        # print(token)
        # print("-" * 25)

        converter = PascalToCppConverter(tokens)
        cpp_code = converter.parse()

        if cpp_code:
            print("--- 转换成功: C++ 代码 ---")
            print(cpp_code)
            print("-" * 25)
        else:
            print("--- 转换失败: 错误信息 ---")
            for error in converter.errors:
                print(error)
            print("-" * 25)

    except SyntaxError as e: 
        print(f"--- 词法分析错误 ---")
        print(e)
        print("-" * 25)
    except Exception as e: 
        print(f"--- 发生意外主程序错误 ---")
        print(e)
        import traceback
        traceback.print_exc()
        print("-" * 25)


# --- 示例测试 ---

pascal_correct1 = """
Var i, J1 : integer;
    Sum   : longint;
    FLAG  : bool;
Begin
    i := 0;
    J1 := 50;
    Sum := 1;
    FLAG := true;
    i := i + 1;
    Sum := J1 - i;
End;
"""

pascal_correct_if_while = """
Var
  count: integer;
  maxCount: integer;
  isValid: bool;
  total: integer;
Begin
  count := 0;
  maxCount := 10;
  isValid := true;
  total := 0;

  if isValid = true then
    maxCount := 20;

  if count < maxCount then
  begin
    count := count + 1;
    total := total + count;
  end
  else
    isValid := false;

  while (count < maxCount) AND isValid do
  begin
    count := count + 1;
    if count = 15 then
      isValid := false;
    total := total + count;
  end;

  sum := total; 
End
"""


pascal_correct_if_while_simplified_condition = """
Var
  count: integer;
  maxCount: integer;
  isValid: bool;
  total: integer;
Begin
  count := 0;
  maxCount := 10;
  isValid := true;
  total := 0;

  if isValid then  
    maxCount := 20;

  if count < maxCount then
  begin
    count := count + 1;
    total := total + count;
  end
  else
    isValid := false;

  while count < maxCount do  
  begin
    count := count + 1;
    if count = 15 then
      isValid := false;
    total := total + count;
  end;
  
  maxcount := total; 
End
"""


print("--- 测试正确示例 1 (Original) ---")
main_convert(pascal_correct1)

print("\n--- 测试正确示例---")
main_convert(pascal_correct_if_while_simplified_condition)

pascal_single_stmt_bodies = """
Var
  x, y, z : integer;
  proceed : bool;
Begin
  x := 10;
  y := 5;
  proceed := true;

  if x > y then
    z := x - y;
  else
    z := y - x;

  if proceed then
    x := x + 1;
  
  y := 0;
  while x > 0 do
  begin
    y := y + x;
    x := x - 1;
    if x = 2 then
        proceed := false;
  end;


  if proceed = false then
      y := 100;

End
"""


print("\n--- 测试正确示例  ---")
main_convert(pascal_single_stmt_bodies)

# Error example: 缺少'then'
pascal_error_if_missing_then = """
Var x: integer;
Begin
  x := 1;
  if x = 1
    x := 2;
End
"""
print("\n--- 测试错误示例 (IF 缺少 THEN) ---")
main_convert(pascal_error_if_missing_then)

# Error example: 缺少 'do'
pascal_error_while_missing_do = """
Var x: integer;
Begin
  x := 10;
  while x > 0
    x := x - 1;
End
"""
print("\n--- 测试错误示例 (WHILE 缺少 DO) ---")
main_convert(pascal_error_while_missing_do)