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
        # text 表示用（符号込み）
        if self.denominator == 1:
            return str(self.numerator)
        return f"{self.numerator}/{self.denominator}"

    def __neg__(self):
        return RawFraction(-self.numerator, self.denominator)

    def __repr__(self):
        return f"RawFraction({self.numerator}, {self.denominator})"

    def to_fraction(self) -> Fraction:
        """標準 Fraction に変換（計算用）"""
        return Fraction(self.numerator, self.denominator)

    # ---- 表示系 ----
    def to_text_abs(self) -> str:
        """絶対値の text 表現"""
        if self.denominator == 1:
            return str(abs(self.numerator))
        return f"{abs(self.numerator)}/{self.denominator}"

    def to_latex_abs(self) -> str:
        """絶対値の LaTeX 表現"""
        if self.denominator == 1:
            return str(abs(self.numerator))
        return f"\\frac{{{abs(self.numerator)}}}{{{self.denominator}}}"

    @property
    def is_negative(self) -> bool:
        return self.numerator < 0

    @property
    def is_zero(self) -> bool:
        return self.numerator == 0


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
