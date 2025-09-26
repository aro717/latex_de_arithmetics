from fractions import Fraction
from .fractions_utils import RawFraction

decimal_places = 2 # デフォルト

def max_2terms(min_val:int, max_val:int, ops:list[str], domain:str, allow_zero:bool) -> int:
    """
    2項全パターン計算
    """
    count = 0
    
    if domain == 'N':
        n_x1 = max_val - max(0, min_val) + 1
    else:
        n_x1 = max_val - min_val + 1

    if not allow_zero and min_val <= 0:
        n_x1 -= 1
    
    for op in ops:
        if op == '-':
            if domain == 'N':
                count += n_x1 * (n_x1 + 1) // 2
            elif domain == 'Z':
                count += n_x1 ** 2
        elif op == '/':
            if min_val <= 0:
                count += n_x1 * (n_x1 - 1)
            else:
                count += n_x1 ** 2
        else:
            count += n_x1 ** 2

    return count

def build_blocks(numbers, operators):
    """
    + / - で区切り、* / のみのブロックに分割
    返り値: (blocks, base_ops)
        blocks: [{'nums':[...], 'ops':[...]}...]
        base_ops: ブロック間の ['+','-','+','-'] の列
    """
    blocks = []
    base_ops = []
    current = {'nums': [], 'ops': []}

    for i, op in enumerate(operators):
        # まず i 番目の数を積む
        current['nums'].append(numbers[i])

        if op in ('*', '/'):
            current['ops'].append(op)
        else:
            # ブロック終了
            blocks.append(current)
            base_ops.append(op)    # ブロック間の + / -
            current = {'nums': [], 'ops': []}

    # 最後の数を積んでラストブロックを追加
    current['nums'].append(numbers[-1])
    blocks.append(current)
    return blocks, base_ops

def value_as_fraction(val):
    if isinstance(val, RawFraction):
        return val.to_fraction()
    return val

def evaluate_blocks(blocks, base_ops):
    """
    +-で分けたblock毎の評価をし、左から+-する
    """
    blocks_values = []
    for blk in blocks:
        current = value_as_fraction(blk['nums'][0])
        for i, op in enumerate(blk['ops']):
            nxt = value_as_fraction(blk['nums'][i + 1])
            if op == '*':
                current *= nxt
            else:
                current /= nxt
        blocks_values.append(current)
    total = blocks_values[0]
    for i, op in enumerate(base_ops):
        if op == '+':
            total += blocks_values[i + 1]
        else:
            total -= blocks_values[i + 1]

    return total

def dict_diff(old: dict, new: dict) -> dict:
    """
    2つのdictの差分を {キー: (old_value, new_value)} の形で返す
    """
    return {
        k: (old.get(k), new.get(k))
        for k in new.keys() | old.keys()  # 両方にあるキーの和集合
        if old.get(k) != new.get(k)
    }

def resource_path(relative_path):
    """appでも正しく参照できるパスを返す"""
    if getattr(sys, 'frozen', False):
        # PyInstaller バンドル内
        base_path = os.path.dirname(sys.executable)
    else:
        # 通常の Python 実行
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

def paren_if_negative(val, first_paren=False, is_first=False, is_negative=None):
    """
    val: 数値 or LaTeX文字列
    is_negative: True/False/None
        - None の場合は val から自動判定（数値なら符号チェック）
        - RawFraction など LaTeX文字列の場合は呼び出し側で指定
    """

    # 符号判定
    if is_negative is None:
        if isinstance(val, (int, float, Fraction)):
            is_negative = val < 0
        else:
            # LaTeX 文字列の場合はフラグ必須
            is_negative = False  

    # 絶対値文字列化
    if isinstance(val, str):
        latex_val = val
    elif isinstance(val, (Fraction, RawFraction)):
        latex_val = f"{abs(val.numerator)}/{val.denominator}"
    else:
        latex_val = str(abs(val))

    if is_negative:
        if first_paren or not is_first:
            return f"(-{latex_val})"
        else:
            return f"-{latex_val}"
    else:
        return latex_val

def format_polynomial(coeffs, forms, mode='text'):
    """
    coeffs: 係数リスト (int, Fraction, RawFraction)
    forms: 単項式リスト ['x', 'y', 'x^2', ...] など
    mode: 'text' | 'latex'
    """
    terms = []
    first = True
    for c, f in zip(coeffs, forms):
        if hasattr(c, "is_zero") and c.is_zero:
            continue
        if not hasattr(c, "is_zero") and c == 0:
            continue

        # 符号と絶対値文字列
        if isinstance(c, RawFraction):
            neg = c.is_negative
            abs_str = c.to_text_abs() if mode == "text" else c.to_latex_abs()
        elif isinstance(c, Fraction):
            neg = c < 0
            abs_str = str(abs(c.numerator)) if c.denominator == 1 else (
                str(abs(c)) if mode == "text" else f"\\frac{{{abs(c.numerator)}}}{{{c.denominator}}}"
            )
        else:  # int, float
            neg = c < 0
            abs_str = str(abs(c))

        # 係数文字列
        if neg:
            coeff_str = "-" if abs_str == "1" and f else "-" + abs_str
        else:
            if first:
                coeff_str = "" if abs_str == "1" and f else abs_str
            else:
                coeff_str = "+" + ("" if abs_str == "1" and f else abs_str)

        terms.append(f"{coeff_str}{f}")
        first = False

    return "".join(terms) if terms else "0"
