import re
from math import gcd
from fractions import Fraction
from utils.fractions_utils import RawFraction
from utils.utils import build_blocks, evaluate_blocks

def latex_tokenize(latex_str: str):
    r"""
    LaTeX 式をトークン化
    - 符号付き整数、符号付き分数
    - 括弧 ()
    - 演算子 +, -, \times, \div
    """
    s = re.sub(r'\\(?:item|displaystyle|left|right|vfill)', '', latex_str)
    s = s.replace('$', '').strip()

    token_pattern = re.compile(
        r'-?\\frac\{\d+\}\{\d+\}'  # 符号付き分数
        r'|-?\d+'                   # 符号付き整数
        r'|\+|\-|\\times|\\div'     # 演算子
    )

    return [t for t in token_pattern.findall(s) if t.strip()]

#--- Arithmetic ---
def parse_single_value(token: str):
    """
    単一値の変換
    - 整数や符号付き整数
    - 符号付き分数
    """
    s = token.strip()

    # 分数
    m = re.fullmatch(r'-?\\frac\{(-?\d+)\}\{(-?\d+)\}', s)
    if m:
        num = int(m.group(1))
        denom = int(m.group(2))
        if s.startswith("-\\frac") and num > 0:
            num = -num
        if denom == 1:
            return num
        elif gcd(num, denom) == 1:
            return Fraction(num, denom)
        else:
            return RawFraction(num, denom)

    # 整数
    return int(s)

def parse_expression(tokens):
    stack = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in ('+', '-', r'\times', r'\div'):
            stack.append('*' if t == r'\times' else '/' if t == r'\div' else t)
        else:
            # 値
            stack.append(parse_single_value(t))
        i += 1
    return stack

def parse_latex_expr(latex_str: str, prob_type: str, var_type: str = None, var_set: str = None):
    if prob_type == 'arithmetic':
        tokens = latex_tokenize(latex_str)
        expr_list = parse_expression(tokens)

        # 値と演算子に分割
        expr_values = expr_list[::2]  # 偶数インデックス → 値
        operators = expr_list[1::2]   # 奇数インデックス → 演算子

        blocks, base_ops = build_blocks(expr_values, operators)
        solve = evaluate_blocks(blocks, base_ops)
        return {
            'vals_ops': [expr_values, operators],
            'solve': solve
        }
    elif prob_type == 'expand':
        # var_type と var_set を元に vars を作成
        if var_set.startswith('a'):
            letters = ['a','b','c','d','e','f']
        else:
            letters = ['x','y','z','w','u','v']

        if var_type == '[x]':
            vars = [letters[0], '1']  # 1変数
        elif var_type == '[x,y]':
            vars = letters[:2]
        elif var_type == '[x,y,z]':
            vars = letters[:3]
        else:
            vars = [letters[0]]  # デフォルト

        # 括弧内の因子を抽出
        # factors = re.findall(r'\(([^)]+)\)', latex_str)
        # expr_values = [parse_multi_var_poly(factor, vars) for factor in factors]
        expr_values = parse_polynomial(latex_str, vars)

        return {
            'expr_values': expr_values,
            'solve': None
        }
    else:
        raise ValueError(f"Unknown problem type: {prob_type}")


def parse_text_expr(expr_text: str, prob_type: str, var_type: str = None, var_set: str = None):
    """
    Textビューの式文字列から expr_values, operators, solve を生成
    """
    # 末尾の = を除去
    expr_text = expr_text.rstrip().rstrip('=').rstrip()
    if prob_type == 'arithmetic':
        parts = expr_text.split()

        expr_values = []
        operators = []

        i = 0
        while i < len(parts):
            tok = parts[i]

            if tok in ('+', '-', '×', '÷'):
                if tok == '×':
                    operators.append('*')
                elif tok == '÷':
                    operators.append('/')
                else:
                    operators.append(tok)
                i += 1
            else:
                # 数値・分数の処理
                val_str = tok
                # 括弧付き負の数: "(-2/3)" -> "-2/3"
                if val_str.startswith('(') and val_str.endswith(')'):
                    val_str = val_str[1:-1]

                # Fraction 判定
                if '/' in val_str:
                    num, denom = val_str.split('/')
                    val = Fraction(int(num), int(denom))
                else:
                    val = int(val_str)
                expr_values.append(val)
                i += 1
        # solve を計算
        solve = expr_values[0]
        for op, val in zip(operators, expr_values[1:]):
            if op == '+':
                solve += val
            elif op == '-':
                solve -= val
            elif op == '*':
                solve *= val
            elif op == '/':
                solve /= val

        return {
            'vals_ops': [expr_values, operators],
            'solve': solve
        }
    elif prob_type == 'expand':
        # var_type と var_set を元に vars を作成
        if var_set.startswith('a'):
            letters = ['a','b','c','d','e','f']
        else:
            letters = ['x','y','z','w','u','v']

        if var_type == '[x]':
            vars = [letters[0], '1']  # 1変数
        elif var_type == '[x,y]':
            vars = letters[:2]
        elif var_type == '[x,y,z]':
            vars = letters[:3]
        else:
            vars = [letters[0]]  # デフォルト

        # 括弧内の因子を抽出
        expr_values = parse_polynomial(expr_text, vars)

        return {
            'expr_values': expr_values,
            'solve': None
        }
    else:
        raise ValueError(f"Unknown problem type: {prob_type}")

# --- Expand ---
def parse_multi_var_poly(factor: str, vars: list[str]):
    """
    複数変数多項式を係数リストに変換
    vars に '1' を入れると定数項を自動で取得
    """
    s = factor.replace('-', '+-')
    terms = [t for t in s.split('+') if t]

    coeff_list = []

    def parse_coef(term: str):
        # \frac{a}{b} を Fraction に変換
        frac_match = re.fullmatch(r'(-?)\\frac{(-?\d+)}{(-?\d+)}', term)
        if frac_match:
            sign, num, denom = frac_match.groups()
            coef = Fraction(int(num), int(denom))
            if sign == '-':
                coef *= -1
            return coef

        # a/b 形式（整数同士の分数）
        frac_match2 = re.fullmatch(r'(-?\d+)/(-?\d+)', term)
        if frac_match2:
            num, denom = frac_match2.groups()
            return Fraction(int(num), int(denom))

        # 整数のみ
        if re.fullmatch(r'-?\d+', term):
            return Fraction(int(term))

        return None

    for var in vars:
        c = 0
        for term in terms:
            term = term.strip()
            if not term:
                continue

            if var == '1':
                # 定数項: term が他の変数を含んでいなければ定数
                if all(v not in term for v in vars if v != '1'):
                    coef = parse_coef(term)
                    if coef is not None:
                        c += coef
            else:
                # 変数項
                pattern = (
                    r'((-?(?:\\frac{[0-9\-]+}{[0-9]+}|[0-9]+/[0-9]+|\d+))?)'  # \frac{}{} or a/b or 整数
                    + re.escape(var)
                    + r'(?:\^(\d+))?'
                )
                m = re.search(pattern, term)
                if m:
                    coef_str, frac_part, deg_str = m.group(1), m.group(2), m.group(3)

                    # coef 部分のパース
                    if coef_str in ('', '+', None):
                        coef = Fraction(1)
                    elif coef_str == '-':
                        coef = Fraction(-1)
                    else:
                        print(coef_str)
                        coef = parse_coef(coef_str)
                        if coef is None:  # 例えば "3" の場合
                            coef = Fraction(int(coef_str))

                    c += coef
        coeff_list.append(c)
    return coeff_list

def parse_polynomial(expr: str, vars: list[str]):
    """
    括弧つき多項式を係数リストに変換
    expr: "(x^2+xy+1)(x+y)" のような式
    vars: ['x','y','z','1'] の順で変数と定数を指定
    return: [[1,0,1,0],[1,1,0,0]] のように各括弧ごとにリスト化
    """
    factors = re.findall(r'\(([^)]+)\)', expr)
    result = []
    for factor in factors:
        coeffs = parse_multi_var_poly(factor, vars)
        result.append(coeffs)
    return result

# --- TAG抽出 ---
def extract_tag_from_tex(tex: str, tag: str):
    """
    tex の先頭行以外も含めて %TAG=... を検索し返す。
    tag は大文字小文字問わずマッチ。
    """
    pattern = re.compile(rf"%\s*{tag}\s*=\s*(.*)", re.IGNORECASE)
    for line in tex.splitlines():
        m = pattern.match(line)
        if m:
            value = m.group(1).strip()
            if value:
                return value
    return None
