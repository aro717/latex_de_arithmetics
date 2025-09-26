from fractions import Fraction
from utils.fractions_utils import RawFraction
from utils.utils import paren_if_negative
from .base import ProblemBase


class ArithmeticProblem(ProblemBase):
    def __init__(self, data, settings):
        super().__init__(data, settings)
        vals_ops = data.get('vals_ops', [])
        self.expr_values = vals_ops[0]
        self.operators = vals_ops[1]

    def to_text(self) -> str:
        parts = []
        for i, val in enumerate(self.expr_values):
            if i==0:
                parts.append(paren_if_negative(val, self.first_paren, is_first=True))
            else:
                parts.append(paren_if_negative(val))
            # 演算子変換
            if i < len(self.operators):
                op = self.operators[i]
                if op == '*':
                    parts.append('×')
                elif op == '/':
                    parts.append('÷')
                else:
                    parts.append(op)
        # show_equalがTrueなら末尾に「=」を付ける
        if self.show_equal:
            if parts[-1] != '=':
                parts.append('=')
        return ' '.join(map(str, parts))

    # --- LaTeX 文字列化 --- #
    def _format_latex(self, pdf_mode=False, show_answer=False, boxed=True) -> str:
        """符号や分数、演算子を LaTeX 用に整形"""
        parts = []
        for i, val in enumerate(self.expr_values):
            if isinstance(val, RawFraction):
                latex_val = val.to_latex()
                if i == 0:
                    parts.append(paren_if_negative(latex_val, self.first_paren, is_first=True, is_negative=val.is_negative))
                else:
                    parts.append(paren_if_negative(latex_val, is_negative=val.is_negative))
            elif isinstance(val, Fraction):
                num, den = val.numerator, val.denominator
                if num == 0:
                    parts.append('0')
                elif num < 0:
                    if self.first_paren or i!=0:
                        parts.append(f'(-\\frac{{{abs(num)}}}{{{den}}})')
                    else:
                        parts.append(f'-\\frac{{{abs(num)}}}{{{den}}}')
                else:
                    parts.append(f'\\frac{{{num}}}{{{den}}}')
            else:
                if i==0:
                    parts.append(paren_if_negative(val, self.first_paren, is_first=True))
                else:
                    parts.append(paren_if_negative(val))
            # 演算子変換
            if i < len(self.operators):
                op = self.operators[i]
                if op == '*':
                    parts.append(r'\times')
                elif op == '/':
                    parts.append(r'\div')
                else:
                    parts.append(op)

        latex = ' '.join(map(str, parts))
        # 括弧変換 (PDF時のみ \left/\right)
        if pdf_mode:
            latex = latex.replace('(', r'\left(').replace(')', r'\right)')
        # show_equalがTrueなら末尾に「=」を付ける
        if self.show_equal or show_answer:
            latex = latex.rstrip()  # 念のため空白除去
            if not latex.endswith('='):
                if self.line_break and pdf_mode:
                    latex += r'\\[1zh] ='
                else:
                    latex += ' ='
        if show_answer:
            if boxed:
                latex += f'\\boxed{{{str(self.solve)}}}'
            else:
                latex += f'{str(self.solve)}'
        return latex
