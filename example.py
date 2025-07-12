import re
import sys

# --- 1. 词法分析 (Lexer) ---

# 定义 Token 类型
TOKENS = {
    'KEYWORD': r'\b(var|integer|longint|bool|begin|end)\b', 
    'IDENTIFIER': r'[a-zA-Z][a-zA-Z0-9]*',
    'INTEGER_LITERAL': r'[0-9]+',
    'ASSIGN': r':=',
    'OP_ADD': r'\+',
    'OP_SUB': r'-',
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
    # 在这里添加 flags=re.IGNORECASE
    for mo in re.finditer(token_regex, code, flags=re.IGNORECASE): 
        kind = mo.lastgroup #Token 类型
        value = mo.group() #Token 值
        column = mo.start() - line_start + 1 #列号

        if kind == 'WHITESPACE':
            if '\n' in value:
                line_num += value.count('\n')
                line_start = mo.end() - value.rfind('\n') -1
            continue 
        elif kind == 'MISMATCH':
            raise SyntaxError(f"错误 (行 {line_num}, 列 {column}): 非法字符 '{value}'")

        #大小写不敏感
        if kind == 'KEYWORD' or kind == 'IDENTIFIER':
             value = value.lower() 

        tokens.append({'type': kind, 'value': value, 'line': line_num, 'col': column})

    tokens.append({'type': 'EOF', 'value': None, 'line': line_num, 'col': -1}) 
    return tokens

# --- 2. 语法/语义分析 与 代码生成  ---
# 语法分析采用自顶向下一次扫描的方法
# 语义分析和代码生成在同一阶段完成
class PascalToCppConverter:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current_token_index = 0
        self.current_token = self.tokens[0]
        self.symbol_table = {} # 符号表: {'var_name_lower': {'type': 'pascal_type', 'cpp_type': 'c++_type'}}
        self.cpp_declarations = [] # 存储 C++ 变量声明
        self.cpp_body = [] # 存储 C++ 实现体代码
        self.errors = [] # 存储错误信息

    def _next_token(self):
        """前进到下一个 Token"""
        self.current_token_index += 1
        if self.current_token_index < len(self.tokens):
            self.current_token = self.tokens[self.current_token_index]
        else:
            # 防止索引越界，但理论上应该由 EOF 处理
            self.current_token = {'type': 'EOF', 'value': None, 'line': -1, 'col': -1}

    def _error(self, message):
        """记录错误信息"""
        token = self.current_token
        err_msg = f"错误 (行 {token.get('line', '?')}, 列 {token.get('col', '?')}): {message}"
        # 尝试指出出错的 Token 值
        if token.get('value') is not None:
           err_msg += f" (遇到: '{token['value']}')"
        elif token['type'] != 'EOF':
             err_msg += f" (遇到 Token 类型: {token['type']})"

        self.errors.append(err_msg)
        raise SyntaxError(err_msg)

    def _expect(self, token_type, expected_value=None):
        """检查当前 Token 是否符合预期类型（和值），如果不符合则报错，符合则前进"""
        if self.current_token['type'] == token_type:
            if expected_value is None or self.current_token['value'] == expected_value:
                token_value = self.current_token['value']
                self._next_token()
                return token_value # 返回符合预期的 Token 的值
            else:
                self._error(f"期望得到 '{expected_value}' 但得到了 '{self.current_token['value']}'")
        else:
            expected_desc = f"'{expected_value}'" if expected_value else f"类型 '{token_type}'"
            self._error(f"期望得到 {expected_desc} 但得到了类型 '{self.current_token['type']}'")

    def _parse_type(self):
        """解析变量类型"""
        token = self.current_token
        if token['type'] == 'KEYWORD' and token['value'] in ['integer', 'longint', 'bool']:
            pascal_type = token['value']
            self._next_token()
            # 映射到 C++ 类型，因为后面要翻译
            if pascal_type == 'integer':
                return pascal_type, 'int'
            elif pascal_type == 'longint':
                return pascal_type, 'long long'
            elif pascal_type == 'bool':
                return pascal_type, 'bool'
        else:
            self._error("期望得到类型关键字 (integer, longint, bool)")

    def _parse_var_declaration(self):
        """解析 var 声明块"""
        self._expect('KEYWORD', 'var')
        # Var 关键字后面应该至少有一个空格，Lexer 会将其作为 WHITESPACE 跳过
        # 我们只需检查下一个 token 是不是 IDENTIFIER
        if self.current_token['type'] != 'IDENTIFIER':
             # 模拟 "Var后缺空格" 或 "Var后直接跟了非法字符" 的错误
             # 实际是因为 Var 后面不是合法的标识符开头
            self._error("关键字 'var' 后面需要跟变量名")

        while self.current_token['type'] == 'IDENTIFIER':
            variables = []
            variables.append(self._expect('IDENTIFIER'))

            while self.current_token['type'] == 'COMMA':
                self._next_token() # 跳过逗号
                variables.append(self._expect('IDENTIFIER'))

            self._expect('COLON')
            pascal_type, cpp_type = self._parse_type()

            # 检查并注册变量到符号表
            cpp_declaration_line = f"{cpp_type} "
            var_names_in_line = []
            for var_name in variables:
                if var_name in self.symbol_table:
                    self._error(f"变量 '{var_name}' 重复定义")
                if not re.match(r'^[a-zA-Z][a-zA-Z0-9]*$', var_name):
                     # 这个检查理论上 Lexer 就完成了，但可以再加一层保险
                     self._error(f"非法变量名 '{var_name}'")
                
                self.symbol_table[var_name] = {'type': pascal_type, 'cpp_type': cpp_type}
                var_names_in_line.append(var_name)

            cpp_declaration_line += ", ".join(var_names_in_line) + ";"
            self.cpp_declarations.append(cpp_declaration_line)

            self._expect('SEMICOLON')
            # 继续处理下一行声明，或者结束 var 块

    def _parse_factor(self):
        """解析表达式的因子"""
        token = self.current_token
        if token['type'] == 'IDENTIFIER':
            var_name = token['value']
            if var_name not in self.symbol_table:
                self._error(f"使用了未定义的变量 '{var_name}'")
            self._next_token()
            return var_name # 返回 C++ 中对应的变量名 (已转小写)
        elif token['type'] == 'INTEGER_LITERAL':
            value = token['value']
            self._next_token()
            return value # 返回数字字符串
        else:
            self._error("表达式中期望得到变量或数字")

    def _parse_term(self):
        # 解析因子
        return self._parse_factor()

    def _parse_expression(self):
        """解析表达式 """
        cpp_expr = self._parse_term()
        while self.current_token['type'] in ['OP_ADD', 'OP_SUB']:
            op_token = self.current_token
            self._next_token()
            right_term = self._parse_term()
            cpp_expr += f" {op_token['value']} {right_term}" # 直接使用 + 或 -
        return cpp_expr

    def _parse_assignment_statement(self):
        """解析赋值语句: Identifier := Expression ;"""
        var_name = self._expect('IDENTIFIER')
        if var_name not in self.symbol_table:
             self._error(f"尝试给未定义的变量 '{var_name}' 赋值")

        self._expect('ASSIGN') # 检查 :=
        
        cpp_expr = self._parse_expression()
        
        self._expect('SEMICOLON')

        self.cpp_body.append(f"    {var_name} = {cpp_expr};") # 添加 C++ 赋值语句 (带缩进)

    def _parse_statement(self):
        """解析单条语句"""
        if self.current_token['type'] == 'IDENTIFIER':
            self._parse_assignment_statement()
        # elif self.current_token['type'] == 'KEYWORD' and self.current_token['value'] == 'if':
        #     self._parse_if_statement()
        else:
            self._error("期望得到语句的开头")


    def _parse_implementation_block(self):
        """解析 begin...end 实现块"""
        self._expect('KEYWORD', 'begin')
        
        # begin 后面可以跟多个语句，直到 end
        # 检查是否直接就是 end
        while not (self.current_token['type'] == 'KEYWORD' and self.current_token['value'] == 'end'):
            if self.current_token['type'] == 'EOF':
                 self._error("代码在 'end' 之前意外结束")
            self._parse_statement() # 解析一条语句

        self._expect('KEYWORD', 'end')
        # Pascal 的主程序块后面可能跟句号 '.' 或 分号 ';'
        # 在这个简化版里，我们假设 end 后面就是结束了，或者跟一个分号（如果后面还有代码）
        # 我们这里强制要求 end 后面要么是 EOF 要么是分号（如果允许嵌套块）
        # 对于顶级块，我们期望后面是 EOF 或没有更多内容了
        # 考虑到简单性，如果后面是分号，我们也接受并前进
        if self.current_token['type'] == 'SEMICOLON':
            self._next_token()
        # 如果后面还有其他非 EOF token，可能是一个语法错误

    def parse(self):
        """执行解析和转换"""
        try:
            # var 块
            if self.current_token['type'] == 'KEYWORD' and self.current_token['value'] == 'var':
                self._parse_var_declaration()

            # 实现块
            self._parse_implementation_block()

            # 检查解析是否到达文件末尾 (允许最后一个 end 后有空白)
            if self.current_token['type'] != 'EOF':
                self._error(f"在 'end' 之后有未预期的内容")

            # 如果没有错误，生成 C++ 代码
            if not self.errors:
                cpp_code = "#include <iostream>\n"
                # 可以根据需要包含其他头文件，例如 <string> 或 <vector>
                # 如果使用了 long long，最好包含 <cstdint> 或确保编译器支持
                cpp_code += "#include <vector>\n" # 示例
                cpp_code += "#include <string>\n" # 示例
                
                # 添加命名空间
                cpp_code += "\nusing namespace std;\n\n"

                # 添加 main 函数
                cpp_code += "int main() {\n"

                # 添加变量声明
                if self.cpp_declarations:
                    cpp_code += "    // Variable declarations\n"
                    for decl in self.cpp_declarations:
                        cpp_code += f"    {decl}\n"
                    cpp_code += "\n"

                # 添加实现体代码
                if self.cpp_body:
                    cpp_code += "    // Implementation\n"
                    for line in self.cpp_body:
                        cpp_code += f"{line}\n"
                    cpp_code += "\n"
                else:
                    cpp_code += "    // No implementation code\n\n"


                # 添加默认的 return 语句
                cpp_code += "    return 0;\n"
                cpp_code += "}\n"
                return cpp_code
            else:
                # 返回错误信息列表
                return None

        except SyntaxError as e:
            # 错误已经被记录在 self.errors 中，这里只是捕获停止信号
            # print(f"解析中止: {e}") # 可以在这里打印错误信息
            return None # 表示转换失败
        except Exception as e:
             # 捕获其他意外错误
             self.errors.append(f"意外内部错误: {e}")
             import traceback
             traceback.print_exc() # 打印详细的堆栈信息
             return None


# --- 3. 主程序 ---

def main(pascal_code):
    """接收 Pascal 代码，尝试转换并打印 C++ 或错误"""
    print("--- 输入 Pascal 代码 ---")
    print(pascal_code)
    print("-" * 25)

    try:
        tokens = lexer(pascal_code)
        # print("--- Tokens ---")
        # for token in tokens:
        #     print(token)
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
        print(f"--- 发生意外错误 ---")
        print(e)
        import traceback
        traceback.print_exc()
        print("-" * 25)


# --- 示例测试 ---

# 正确示例 1
pascal_correct1 = """
Var i, J1 : integer;
    Sum   : longint;
    FLAG  : bool;
Begin
    i := 0;
    J1 := 50;
    Sum := 1;
    FLAG := 1; 
    i := i + 1;
    Sum := J1 - i;
End;
"""

# 正确示例 2 (混合大小写, 不同格式)
pascal_correct2 = """
VAR myVar1, myVar2 : INTEGER; result : LONGINT; active : BOOL;
BEGIN
    myVar1 := 100;
    myVar2 := 25;
    Result := myVar1 + myVar2;
    active := 0;
    result := Result - 5;
end
"""

# 错误示例: Var 后缺空格 (Lexer/Parser 会捕捉到 'Vari' 不是合法标识符或关键字)
pascal_error1 = """
Vari:integer;
Begin
End
"""

# 错误示例: 变量以数字开头 (Lexer 会报错)
pascal_error2 = """
Var 9I:integer;
Begin
End
"""

# 错误示例: 多变量缺分割符 (Parser 会在 ':' 前期望 ';' 或 'IDENTIFIER' 时报错)
pascal_error3 = """
Var i  j:integer;
Begin
End
"""

# 错误示例: 变量含非法字符 (Lexer 会在 '#' 处报错)
pascal_error4 = """
Var i#:integer;
Begin
End
"""

# 错误示例: 变量声明缺 ; (Parser 在期望 ';' 时遇到 'Begin' 报错)
pascal_error5 = """
Var i3:integer
Begin
End
"""

# 错误示例: 变量重复定义
pascal_error6 = """
Var i3:integer;
    i3:bool;
Begin
End;
"""

# 错误示例: 使用未定义变量
pascal_error7 = """
Var x : integer;
Begin
    y := x + 1; // y 未定义
End
"""

# 错误示例: 赋值语句缺少 :
pascal_error8 = """
Var count : integer;
Begin
    count = 0; // 应该是 :=
End
"""

# 运行测试
print("--- 测试正确示例 1 ---")
main(pascal_correct1)

print("\n--- 测试正确示例 2 ---")
main(pascal_correct2)

# print("\n--- 测试错误示例 1 (Var后缺空格/非法标识符) ---")
# main(pascal_error1) # 可能报 "关键字 'var' 后面需要跟变量名" 或 词法错误 "非法字符 'V'" 取决于实现细节

# print("\n--- 测试错误示例 2 (变量以数字开头) ---")
# main(pascal_error2) # Lexer 应该报非法字符 '9'

# print("\n--- 测试错误示例 3 (多变量缺分割符) ---")
# main(pascal_error3) # Parser 应该在 ':' 处报错

# print("\n--- 测试错误示例 4 (变量含非法字符) ---")
# main(pascal_error4) # Lexer 应该报非法字符 '#'

# print("\n--- 测试错误示例 5 (变量声明缺 ;) ---")
# main(pascal_error5) # Parser 应该在 'Begin' 处报错，期望 ';'

# print("\n--- 测试错误示例 6 (变量重复定义) ---")
# main(pascal_error6) # Parser 应该报变量 'i3' 重复定义

# print("\n--- 测试错误示例 7 (使用未定义变量) ---")
# main(pascal_error7) # Parser 应该在 'y := ...' 处报错 'y' 未定义，或者在 '... = x + 1' 处报错（如果先检查右侧）

# print("\n--- 测试错误示例 8 (赋值语句缺 :) ---")
# main(pascal_error8) # Parser 应该在 '=' 处报错，期望 ':='