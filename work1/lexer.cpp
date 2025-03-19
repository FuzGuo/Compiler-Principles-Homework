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
    OPERATOR_ASSIGN,    // :=
    OPERATOR_LT,        // <
    OPERATOR_GT,        // >
    OPERATOR_NE,        // <>
    OPERATOR_GE,        // >=
    OPERATOR_LE,        // <=
    OPERATOR_EQ,        // ==
    DELIMITER_SEMICOLON, // ;
    DELIMITER_COLON,     // :
    DELIMITER_LPAREN,    // (
    DELIMITER_RPAREN,    // )
    DELIMITER_COMMA,     // ,
    IDENTIFIER,
    NUMBER,
    ERROR
};

struct Token {
    TokenType type;
    std::string value;
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
            errors.push_back("Empty program");
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
    std::unordered_set<std::string> keywords;
    std::unordered_set<std::string> types;
    std::unordered_map<std::string, std::string> symbolTable; // Identifier -> Type
    std::vector<std::string> errors;

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
        return ERROR;
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
        return tokens;
    }

    Token readIdentifierOrKeyword() {
        std::string tokenStr;
        // size_t startPos = pos;

        // 读取直到遇到空白或分隔符
        while (pos < source.length() && !std::isspace(source[pos]) && !isDelimiter(source[pos])) {
            tokenStr += source[pos];
            pos++;
        }

        std::string lowerToken = toLower(tokenStr);

        // 检查是否为关键字
        if (keywords.count(lowerToken)) {
            return {getKeywordType(lowerToken), tokenStr};
        }

        // 验证标识符合法性：必须以字母开头，之后只允许字母和数字
        if (!std::isalpha(tokenStr[0])) {
            return {ERROR, tokenStr}; // 以数字或其他字符开头
        }
        for (char c : tokenStr) {
            if (!std::isalnum(c)) {
                return {ERROR, tokenStr}; // 包含非法字符
            }
        }

        return {IDENTIFIER, tokenStr};
    }

    bool isDelimiter(char c) {
        return c == ';' || c == ':' || c == ',' || c == '(' || c == ')' || c == '+' || c == '-' ||
               c == '*' || c == '/' || c == '<' || c == '>' || c == '=';
    }

    Token readNumber() {
        std::string tokenStr;
        while (pos < source.length() && std::isdigit(source[pos])) {
            tokenStr += source[pos];
            pos++;
        }
        return {NUMBER, tokenStr};
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
            return {ERROR, "="}; // Standalone '=' is invalid
        }
        std::string invalid(1, c);
        pos++;
        return {ERROR, invalid};
    }

    void parse() {
        if (tokenPos >= tokens.size() || tokens[tokenPos].type != KEYWORD_VAR) {
            errors.push_back("Program must start with 'var'");
            return;
        }
        tokenPos++; // Skip 'var'

        parseDefinitionBody();
        if (errors.empty() && (tokenPos >= tokens.size() || tokens[tokenPos].type != KEYWORD_BEGIN)) {
            errors.push_back("Missing 'begin' after definition body");
            return;
        }
        if (!errors.empty()) return; // Stop if definition body has errors
        tokenPos++; // Skip 'begin'
        parseRealizationBody();
        if (errors.empty() && (tokenPos >= tokens.size() || tokens[tokenPos].type != KEYWORD_END)) {
            errors.push_back("Missing 'end' at program termination");
        }
    }

    void parseDefinitionBody() {
        while (tokenPos < tokens.size() && tokens[tokenPos].type != KEYWORD_BEGIN) {
            if (tokens[tokenPos].type == ERROR) {
                errors.push_back("Invalid identifier: " + tokens[tokenPos].value);
                tokenPos++;
                return; // 停止解析定义体
            }
            if (tokens[tokenPos].type != IDENTIFIER) {
                errors.push_back("Expected identifier, found: " + tokens[tokenPos].value);
                tokenPos++;
                return;
            }
            std::string varName = tokens[tokenPos].value;
            tokenPos++;

            std::vector<std::string> vars = {varName};
            while (tokenPos < tokens.size() && tokens[tokenPos].type == DELIMITER_COMMA) {
                tokenPos++;
                if (tokenPos >= tokens.size() || tokens[tokenPos].type != IDENTIFIER) {
                    errors.push_back("Expected identifier after comma");
                    return;
                }
                if (tokens[tokenPos].type == ERROR) {
                    errors.push_back("Invalid identifier: " + tokens[tokenPos].value);
                    tokenPos++;
                    return;
                }
                vars.push_back(tokens[tokenPos].value);
                tokenPos++;
            }
            if (tokenPos < tokens.size() && tokens[tokenPos].type == IDENTIFIER) {
                errors.push_back("Missing comma between identifiers");
                return;
            }

            if (tokenPos >= tokens.size() || tokens[tokenPos].type != DELIMITER_COLON) {
                errors.push_back("Missing ':' after variable(s)");
                return;
            }
            tokenPos++;

            if (tokenPos >= tokens.size() || !types.count(toLower(tokens[tokenPos].value))) {
                errors.push_back("Expected type (integer, longint, bool), found: " +
                                 (tokenPos < tokens.size() ? tokens[tokenPos].value : "none"));
                return;
            }
            std::string varType = toLower(tokens[tokenPos].value);
            tokenPos++;

            for (const auto& var : vars) {
                if (symbolTable.count(var)) {
                    errors.push_back("Repeated definition of variable: " + var);
                    return;
                }
                symbolTable[var] = varType;
            }

            if (tokenPos >= tokens.size() || tokens[tokenPos].type != DELIMITER_SEMICOLON) {
                errors.push_back("Missing ';' after variable declaration");
                return;
            }
            tokenPos++;
        }
    }

    void parseRealizationBody() {
        while (tokenPos < tokens.size() && tokens[tokenPos].type != KEYWORD_END) {
            if (tokens[tokenPos].type == ERROR) {
                errors.push_back("Invalid token in realization: " + tokens[tokenPos].value);
                tokenPos++;
                return;
            }
            if (tokens[tokenPos].type != IDENTIFIER) {
                errors.push_back("Expected identifier in statement, found: " + tokens[tokenPos].value);
                tokenPos++;
                return;
            }
            std::string varName = tokens[tokenPos].value;
            if (!symbolTable.count(varName)) {
                errors.push_back("Undefined variable: " + varName);
                return;
            }
            tokenPos++;

            if (tokenPos >= tokens.size() || tokens[tokenPos].type != OPERATOR_ASSIGN) {
                errors.push_back("Missing ':=' after identifier: " + varName);
                return;
            }
            tokenPos++;

            if (tokenPos >= tokens.size() || (tokens[tokenPos].type != NUMBER && tokens[tokenPos].type != IDENTIFIER)) {
                errors.push_back("Expected number or identifier after ':=', found: " +
                                 (tokenPos < tokens.size() ? tokens[tokenPos].value : "none"));
                return;
            }
            if (tokens[tokenPos].type == IDENTIFIER && !symbolTable.count(tokens[tokenPos].value)) {
                errors.push_back("Undefined variable in assignment: " + tokens[tokenPos].value);
                return;
            }
            tokenPos++;

            if (tokenPos >= tokens.size() || tokens[tokenPos].type != DELIMITER_SEMICOLON) {
                errors.push_back("Missing ';' after assignment");
                return;
            }
            tokenPos++;
        }
    }

    void reportErrors() {
        if (errors.empty()) {
            std::cout << "Analysis successful: No errors found.\n";
        } else {
            std::cout << "Errors found:\n";
            for (const auto& error : errors) {
                std::cout << "- " << error << "\n";
            }
        }
    }
};

int main() {
    std::vector<std::string> testCases = {
        "Var i,j:integer;Begin i:=0;j:=1;End",           // Correct
        "Vari:integer;",                                 // Missing space after var
        "Var 9i:integer;",                               // Starts with digit
        "Var i j:integer;",                              // Missing comma
        "Var i#:integer;",                               // Illegal character
        "Var i:integer",                                 // Missing semicolon
        "Var i:integer;i:bool;",                         // Repeated definition
        "Var i:integer;Begin i=0;End",                   // Missing :=
        "Var i:integer;Begin j:=0;End",                  // Undefined variable
        "Var i,J1:integer;Begin i:=0 J1:=50;End"         // Missing semicolon in realization
    };

    for (const auto& test : testCases) {
        std::cout << "\nTesting: " << test << "\n";
        Analyzer analyzer(test);
        analyzer.analyze();
    }

    return 0;
}