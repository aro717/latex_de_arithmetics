from .base import ProblemBase
from utils.utils import format_polynomial


class ExpandProblem(ProblemBase):
    def __init__(self, data, settings):
        super().__init__(data, settings)
        self.expr_values = data['expr_values']   # [[1,2], [3,4]] みたいな係数リスト
        self.var_set = settings['var_set']
        self.var_type = settings['var_type']
        self.n_polys = settings['n_polys']
        self.monic = settings.get('monic', False)
        self.min_terms = int(settings['min_terms'])
        self.max_terms = int(settings['max_terms'])

    def to_text(self) -> str:
        if self.var_set.startswith('a'):
            letters = ['a', 'b', 'c', 'd', 'e', 'f']
        else:
            letters = ['x', 'y', 'z', 'w', 'u', 'v']

        parts = []
        for coeffs in self.expr_values:
            forms = self.get_forms(self.var_type, len(coeffs), letters)
            poly_str = format_polynomial(coeffs, forms, mode='text')
            parts.append(f'({poly_str})')

        # show_equalがTrueなら末尾に「=」を付ける
        if self.show_equal:
            if parts[-1] != '=':
                parts.append('=')
        return ' '.join(map(str, parts))

    def _format_latex(self, pdf_mode=False, show_answer=False, boxed=True):
        # --- 使用する変数を決定 ---
        if self.var_set.startswith('a'):
            letters = ['a', 'b', 'c', 'd', 'e', 'f']
        else:
            letters = ['x', 'y', 'z', 'w', 'u', 'v']

        parts = []
        for coeffs in self.expr_values:
            forms = self.get_forms(self.var_type, len(coeffs), letters)
            poly_str = format_polynomial(coeffs, forms, mode='latex')
            parts.append(poly_str)

        # --- まとめて式にする ---
        latex = ''.join([f'({p})' for p in parts])

        # 括弧変換 (PDF時のみ \left/\right)
        if pdf_mode:
            latex = latex.replace('(', r'\left(').replace(')', r'\right)')
        # show_equalがTrueなら末尾に「=」を付ける
        if self.show_equal or show_answer:
            latex = latex.rstrip() # 念のため空白除去
            if not latex.endswith('='):
                if self.line_break and pdf_mode:
                    latex += r'\\[1zh] ='
                else:
                    latex += ' ='
        if show_answer:
            forms = self.get_forms(self.var_type, len(self.solve), letters)
            solve_str = format_polynomial(self.solve, forms, mode='latex')
            if boxed:
                latex += f'\\boxed{{{solve_str}}}'
            else:
                latex += f'{solve_str}'

        return latex

    def get_forms(self, var_type, n_terms, letters):
        """変数の種類と項数から項の形を決める"""
        if var_type == '[x]':
            return [
                f'{letters[0]}^{n_terms - i - 1}' if n_terms - i - 1 > 1
                else (letters[0] if n_terms - i - 1 == 1 else '')
                for i in range(n_terms)
            ]
        elif var_type == '[x,y]':
            if n_terms == 2:
                return [f'{letters[0]}', f'{letters[1]}']
            elif n_terms == 3:
                return [f'{letters[0]}^2', f'{letters[0]}{letters[1]}', f'{letters[1]}^2']
            elif n_terms == 4:
                return [f'{letters[0]}^3', f'{letters[0]}^2{letters[1]}',
                        f'{letters[0]}{letters[1]}^2', f'{letters[1]}^3']
            else:
                return [f'{letters[0]}'] * n_terms
        else:
            return letters[:n_terms]
