from fractions import Fraction


# ------------------------------
# RawFraction:
# ------------------------------
class RawFraction:
    """約分しない分数（表示専用）"""

    __slots__ = ("numerator", "denominator")

    def __init__(self, numerator: int, denominator: int):
        if denominator == 0:
            raise ZeroDivisionError("Denominator cannot be zero.")
        self.numerator = numerator
        self.denominator = denominator

    def __str__(self):
        return f"{self.numerator}/{self.denominator}"

    def __neg__(self):
        return RawFraction(-self.numerator, self.denominator)

    def __repr__(self):
        return f"RawFraction({self.numerator}, {self.denominator})"

    def to_fraction(self) -> Fraction:
        """標準 Fraction に変換（計算用）"""
        return Fraction(self.numerator, self.denominator)

    def to_latex(self) -> str:
        """符号を除いた LaTeX 文字列"""
        return f"\\frac{{{abs(self.numerator)}}}{{{self.denominator}}}"

    @property
    def is_negative(self) -> bool:
        return self.numerator < 0

def normalize_fraction(frac):
    """
    Fraction の符号を分子に寄せて返す。
    - 分母は常に正
    """
    if isinstance(frac, (Fraction, RawFraction)):
        if frac.denominator < 0:
            return frac.__class__(-frac.numerator, -frac.denominator)
        return frac
    else:
        return frac

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

