#include <iostream>
#include <vector>
#include <string>
#include <unordered_set>
#include <unordered_map>
#include <cctype>

enum TokenType {
    KEYWORD_VAR,         
    KEYWORD_INTEGER,     
    KEYWORD_LONGINT,     
    KEYWORD_BOOL,        
    KEYWORD_IF,          
    KEYWORD_THEN,       
    KEYWORD_ELSE,        
    KEYWORD_WHILE,       
    KEYWORD_DO,          
    KEYWORD_FOR,         
    KEYWORD_BEGIN,       
    KEYWORD_END,         
    KEYWORD_AND,         
    KEYWORD_OR,          
    OPERATOR_PLUS,       
    OPERATOR_MINUS,      
    OPERATOR_MULTIPLY,   
    OPERATOR_DIVIDE,     
    OPERATOR_ASSIGN,     
    OPERATOR_LT,         
    OPERATOR_GT,        
    OPERATOR_NE,        
    OPERATOR_GE,         
    OPERATOR_LE,         
    OPERATOR_EQ,         
    DELIMITER_SEMICOLON, 
    DELIMITER_COLON,     
    DELIMITER_LPAREN,   
    DELIMITER_RPAREN,    
    DELIMITER_COMMA,     
    IDENTIFIER,          
    NUMBER,              
    ERROR                
};

struct Token {
    TokenType type;   // token类型
    std::string value; // token值
};

class Analyzer {
public:
    Analyzer(const std::string& src) : source(src), pos(0), tokenPos(0) {
        keywords = {"var", "integer", "longint", "bool", "if", "then", "else",
                    "while", "do", "for", "begin", "end", "and", "or"};
        types = {"integer", "longint", "bool"};
    }

    void analyze() {
        tokens = tokenize();
        if (tokens.empty()) {
            errors.push_back("程序为空");
        } else {
            parse();
        }
        reportErrors();
    }

private:
    std::string source;                          
    size_t pos;                                  
    std::vector<Token> tokens;                   
    size_t tokenPos;                             
    std::unordered_set<std::string> keywords;    // 关键字集合
    std::unordered_set<std::string> types;       // 类型集合
    std::unordered_map<std::string, std::string> symbolTable; // 符号表 标识符 -> 类型
    std::vector<std::string> errors;             // 错误信息列表

    std::string toLower(const std::string& str) {
        std::string lower;
        for (char c : str) {
            lower += std::tolower(static_cast<unsigned char>(c));
        }
        return lower; 
    }

    TokenType getKeywordType(const std::string& keyword) {
        if (keyword == "var") return KEYWORD_VAR;
        if (keyword == "integer") return KEYWORD_INTEGER;
        if (keyword == "longint") return KEYWORD_LONGINT;
        if (keyword == "bool") return KEYWORD_BOOL;
        if (keyword == "if") return KEYWORD_IF;
        if (keyword == "then") return KEYWORD_THEN;
        if (keyword == "else") return KEYWORD_ELSE;
        if (keyword == "while") return KEYWORD_WHILE;
        if (keyword == "do") return KEYWORD_DO;
        if (keyword == "for") return KEYWORD_FOR;
        if (keyword == "begin") return KEYWORD_BEGIN;
        if (keyword == "end") return KEYWORD_END;
        if (keyword == "and") return KEYWORD_AND;
        if (keyword == "or") return KEYWORD_OR;
        return ERROR; // 返回关键字对应的令牌类型
    }

    std::vector<Token> tokenize() {
        std::vector<Token> tokens;
        while (pos < source.length()) {
            char c = source[pos];
            if (std::isspace(c)) {
                pos++; 
            } else if (std::isalpha(c)) {
                tokens.push_back(readIdentifierOrKeyword()); 
            } else if (std::isdigit(c)) {
                tokens.push_back(readNumber()); 
            } else {
                tokens.push_back(readOperator());
            }
        }
        return tokens; // 返回令牌列表
    }

    Token readIdentifierOrKeyword() {
        std::string tokenStr;

        while (pos < source.length() && !std::isspace(source[pos]) && !isDelimiter(source[pos])) {
            tokenStr += source[pos];
            pos++;
        }

        std::string lowerToken = toLower(tokenStr);

        // 检查是否为关键字
        if (keywords.count(lowerToken)) {
            return {getKeywordType(lowerToken), tokenStr};
        }

        // 验证标识符的合法性：必须以字母开头，之后只允许字母和数字
        if (!std::isalpha(tokenStr[0])) {
            return {ERROR, tokenStr}; // 以数字或其他字符开头
        }
        for (char c : tokenStr) {
            if (!std::isalnum(c)) {
                return {ERROR, tokenStr}; // 包含非法字符
            }
        }

        return {IDENTIFIER, tokenStr}; // 返回标识符令牌
    }

    bool isDelimiter(char c) {
        return c == ';' || c == ':' || c == ',' || c == '(' || c == ')' || c == '+' || c == '-' ||
               c == '*' || c == '/' || c == '<' || c == '>' || c == '='; // 判断是否为分隔符
    }

    Token readNumber() {
        std::string tokenStr;
        while (pos < source.length() && std::isdigit(source[pos])) {
            tokenStr += source[pos];
            pos++;
        }
        return {NUMBER, tokenStr}; // 返回数字令牌
    }

    Token readOperator() {
        char c = source[pos];
        if (c == '+') { pos++; return {OPERATOR_PLUS, "+"}; }
        if (c == '-') { pos++; return {OPERATOR_MINUS, "-"}; }
        if (c == '*') { pos++; return {OPERATOR_MULTIPLY, "*"}; }
        if (c == '/') { pos++; return {OPERATOR_DIVIDE, "/"}; }
        if (c == ';') { pos++; return {DELIMITER_SEMICOLON, ";"}; }
        if (c == '(') { pos++; return {DELIMITER_LPAREN, "("}; }
        if (c == ')') { pos++; return {DELIMITER_RPAREN, ")"}; }
        if (c == ',') { pos++; return {DELIMITER_COMMA, ","}; }
        if (c == ':') {
            if (pos + 1 < source.length() && source[pos + 1] == '=') {
                pos += 2;
                return {OPERATOR_ASSIGN, ":="};
            }
            pos++;
            return {DELIMITER_COLON, ":"};
        }
        if (c == '<') {
            if (pos + 1 < source.length()) {
                if (source[pos + 1] == '>') { pos += 2; return {OPERATOR_NE, "<>"}; }
                if (source[pos + 1] == '=') { pos += 2; return {OPERATOR_LE, "<="}; }
            }
            pos++;
            return {OPERATOR_LT, "<"};
        }
        if (c == '>') {
            if (pos + 1 < source.length() && source[pos + 1] == '=') {
                pos += 2;
                return {OPERATOR_GE, ">="};
            }
            pos++;
            return {OPERATOR_GT, ">"};
        }
        if (c == '=') {
            if (pos + 1 < source.length() && source[pos + 1] == '=') {
                pos += 2;
                return {OPERATOR_EQ, "=="};
            }
            pos++;
            return {ERROR, "="}; // 单独的 '=' 是无效的
        }
        std::string invalid(1, c);
        pos++;
        return {ERROR, invalid}; // 返回无效字符的错误令牌
    }

    void parse() {
        if (tokenPos >= tokens.size() || tokens[tokenPos].type != KEYWORD_VAR) {
            errors.push_back("程序起始缺少合法的 'var'");
            return;
        }
        tokenPos++; // 跳过 'var'

        parseDefinitionBody(); // 解析定义部分
        if (errors.empty() && (tokenPos >= tokens.size() || tokens[tokenPos].type != KEYWORD_BEGIN)) {
            errors.push_back("定义部分后缺少 'begin'");
            return;
        }
        if (!errors.empty()) return; // 如果定义部分有错误，则停止
        tokenPos++; // 跳过 'begin'
        parseRealizationBody(); // 解析实现部分
        if (errors.empty() && (tokenPos >= tokens.size() || tokens[tokenPos].type != KEYWORD_END)) {
            errors.push_back("程序结束处缺少 'end'");
        }
    }

    void parseDefinitionBody() {
        while (tokenPos < tokens.size() && tokens[tokenPos].type != KEYWORD_BEGIN) {
            if (tokens[tokenPos].type == ERROR) {
                errors.push_back("无效的标识符: " + tokens[tokenPos].value);
                tokenPos++;
                return; // 停止解析定义部分
            }
            if (tokens[tokenPos].type != IDENTIFIER) {
                errors.push_back("未定义有效标识符: " + tokens[tokenPos].value);
                tokenPos++;
                return;
            }
            std::string varName = tokens[tokenPos].value;
            tokenPos++;

            std::vector<std::string> vars = {varName};
            while (tokenPos < tokens.size() && tokens[tokenPos].type == DELIMITER_COMMA) {
                tokenPos++;
                if (tokenPos >= tokens.size() || tokens[tokenPos].type != IDENTIFIER) {
                    errors.push_back("逗号后期望标识符");
                    return;
                }
                if (tokens[tokenPos].type == ERROR) {
                    errors.push_back("无效的标识符: " + tokens[tokenPos].value);
                    tokenPos++;
                    return;
                }
                vars.push_back(tokens[tokenPos].value);
                tokenPos++;
            }
            if (tokenPos < tokens.size() && tokens[tokenPos].type == IDENTIFIER) {
                errors.push_back("标识符之间缺少逗号");
                return;
            }

            if (tokenPos >= tokens.size() || tokens[tokenPos].type != DELIMITER_COLON) {
                errors.push_back("变量后缺少 ':'");
                return;
            }
            tokenPos++;

            if (tokenPos >= tokens.size() || !types.count(toLower(tokens[tokenPos].value))) {
                errors.push_back("期望类型 (integer, longint, bool)，找到: " +
                                 (tokenPos < tokens.size() ? tokens[tokenPos].value : "无"));
                return;
            }
            std::string varType = toLower(tokens[tokenPos].value);
            tokenPos++;

            for (const auto& var : vars) {
                if (symbolTable.count(var)) {
                    errors.push_back("变量重复定义: " + var);
                    return;
                }
                symbolTable[var] = varType;
            }

            if (tokenPos >= tokens.size() || tokens[tokenPos].type != DELIMITER_SEMICOLON) {
                errors.push_back("变量声明后缺少 ';'");
                return;
            }
            tokenPos++;
        }
    }

    void parseRealizationBody() {
        while (tokenPos < tokens.size() && tokens[tokenPos].type != KEYWORD_END) {
            if (tokens[tokenPos].type == ERROR) {
                errors.push_back("实现部分中的无效令牌: " + tokens[tokenPos].value);
                tokenPos++;
                return;
            }
            if (tokens[tokenPos].type != IDENTIFIER) {
                errors.push_back("语句中期望标识符，找到: " + tokens[tokenPos].value);
                tokenPos++;
                return;
            }
            std::string varName = tokens[tokenPos].value;
            if (!symbolTable.count(varName)) {
                errors.push_back("未定义的变量: " + varName);
                return;
            }
            tokenPos++;

            if (tokenPos >= tokens.size() || tokens[tokenPos].type != OPERATOR_ASSIGN) {
                errors.push_back("标识符后缺少 ':=': " + varName);
                return;
            }
            tokenPos++;

            if (tokenPos >= tokens.size() || (tokens[tokenPos].type != NUMBER && tokens[tokenPos].type != IDENTIFIER)) {
                errors.push_back("':=' 后期望数字或标识符，找到: " +
                                 (tokenPos < tokens.size() ? tokens[tokenPos].value : "无"));
                return;
            }
            if (tokens[tokenPos].type == IDENTIFIER && !symbolTable.count(tokens[tokenPos].value)) {
                errors.push_back("赋值中未定义的变量: " + tokens[tokenPos].value);
                return;
            }
            tokenPos++;

            if (tokenPos >= tokens.size() || tokens[tokenPos].type != DELIMITER_SEMICOLON) {
                errors.push_back("赋值后缺少 ';'");
                return;
            }
            tokenPos++;
        }
    }

    void reportErrors() {
        if (errors.empty()) {
            std::cout << "分析成功：未发现错误。\n";
        } else {
            std::cout << "发现错误：\n";
            for (const auto& error : errors) {
                std::cout << "- " << error << "\n";
            }
        }
    }
};

int main() {
    std::vector<std::string> testCases = {
        "Var i,j:integer;Begin i:=0;j:=1;End",           // 正确示例
        "Vari:integer;",                                 // var后缺少空格
        "Var 9i:integer;",                               // 以数字开头
        "Var i j:integer;",                              // 缺少逗号
        "Var i#:integer;",                               // 非法字符
        "Var i:integer",                                 // 缺少分号
        "Var i:integer;i:bool;",                         // 变量重复定义
        "Var i:integer;Begin i=0;End",                   // 缺少 :=
        "Var i:integer;Begin j:=0;End",                  // 未定义的变量
        "Var i,J1:integer;Begin i:=0 J1:=50;End"         // 实现部分缺少分号
    };

    for (const auto& test : testCases) {
        std::cout << "\n测试: " << test << "\n";
        Analyzer analyzer(test);
        analyzer.analyze();
    }

    return 0;
}