import os
import subprocess
import re
from fractions import Fraction
from fractions_utils import RawFraction, normalize_fraction, paren_if_negative
from math import gcd
from utils import build_blocks, evaluate_blocks


# ------------------------------
# BlockBuilder
# 役割: 複数の Problem をまとめて1つの「ブロック」にする。
# 責任:
#     どのモード（Text, LaTeXビュー, PDF）で出力するかによって変換
#     列数に応じた \columnbreak の挿入
#     番号付きリストの生成
# ポイント: 「問題の列や番号、改行などの見た目」を扱う部分。
# ------------------------------
class BlockBuilder:
    def __init__(self, problems, settings):
        self.problems = problems
        self.settings = settings

    def build_block(self, mode='text_pdf', show_answer=False) -> str:
        """mode: 'latex_pdf' | 'latex_source' | 'text'"""
        num_problems = len(self.problems)
        cols = int(self.settings['cols'])
        per_col = (num_problems + cols - 1) // cols

        problems = []
        for i, p in enumerate(self.problems, start=1):
            if mode == 'latex_pdf':
                problems.append(p.to_latex_pdf(show_answer))
            elif mode == 'latex_source':
                problems.append(p.to_latex_source())
            elif mode == 'text':
                problems.append(f'({i}) {p.to_text()}')
            else:
                raise ValueError(f'Unknown mode {mode}')

            if i % per_col == 0 and i < num_problems:
                if mode.startswith('latex'):
                    problems.append(r'\null\columnbreak')
                elif mode == 'text':
                    problems.append('[改段]')

            if i == num_problems:
                if mode.startswith('latex'):
                    problems.append(r'\null')

        if mode.startswith('latex'):
            return rf"""
\begin{{multicols*}}{{{cols}}}
\begin{{enumerate}}[(1)]
{chr(10).join(problems)}
\end{{enumerate}}
\end{{multicols*}}
""".strip()
        else: # text
            return '\n'.join(problems)

# ------------------------------
# Problem
# 役割: 「1つの問題」を表現。
# 責任:
#     Textビュー向け変換 (to_text())
#     LaTeXビュー向け変換 (to_latex_source())
#     PDF出力向け変換 (to_latex_pdf())
# ポイント: 式の構造に応じて演算子や括弧、分数表記を変換する。
# ------------------------------
class Problem:
    def __init__(self, data=None, first_paren=False, show_equal=True):
        """
        expr_values : List[int|Fraction]  数値のまま保持
        operators   : List[str]            '+','-','*','/' など
        show_equal  : bool
        """
        data = data or {}
        self.expr_str = data.get('expr_str', [])
        self.expr_values = data.get('expr_values', []) # 元の式文字列、例: '1/2', '1*2'
        self.operators = data.get('operators', [])
        self.total = data.get('total', 0)
        self.first_paren = first_paren
        self.show_equal = show_equal
    
    # --- LaTeX 文字列化 --- #
    def _format_latex(self, pdf_mode: bool = False, show_answer: bool = False) -> str:
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
                    parts.append(0)
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
        latex = ' '.join(parts)
        # 括弧変換 (PDF時のみ \left/\right)
        if pdf_mode:
            latex = latex.replace('(', r'\left(').replace(')', r'\right)')
        # show_equalがTrueなら末尾に「=」を付ける
        if self.show_equal or show_answer:
            latex = latex.rstrip()  # 念のため空白除去
            if not latex.endswith('='):
                latex += ' ='
        if show_answer:
            latex += f'\\boxed{{{str(self.total)}}}'
        return latex

    def from_text_to_latex(self, text_expr):
        r"""
        Textビューの式を LaTeX用に正規化
        - × -> \times
        - ÷ -> \div
        - num/denom -> \frac{num}{denom} （マイナスはトップレベルに）
        """
        expr = text_expr

        # ×, ÷ を一旦記号に置換
        expr = expr.replace('×', '*').replace('÷', '/')

        # 分数判定: num/denom 形式
        def frac_repl(m):
            num, denom = m.group(1), m.group(2)
            if num.startswith('-'):
                return f'-\\frac{{{num[1:]}}}{{{denom}}}'
            else:
                return f'\\frac{{{num}}}{{{denom}}}'

        # 単純な整数分数に変換
        expr = re.sub(r'(?<!\\frac{)(-?\d+)/(\d+)', frac_repl, expr)

        # 残りの演算子 * / を LaTeXに変換
        expr = expr.replace('*', r'\times').replace('/', r'\div')

        self.expr = expr
        return expr

    # --- Textビュー用 --- #
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
        return ' '.join(parts)

    # --- LaTeXビュー用 --- #
    def to_latex_source(self) -> str:
        latex = self._format_latex(pdf_mode=False)
        return rf'\item ${latex}$'

    # --- PDF出力用 --- #
    def to_latex_pdf(self, show_answer=False) -> str:
        latex = self._format_latex(pdf_mode=True, show_answer=show_answer)
        return rf'\item $\displaystyle {latex}$\vfill'

    @classmethod
    def from_values(cls, expr_values, operators, total, first_paren, show_equal=True):
        """
        expr_values: 数値または Fraction のリスト
        operators: ['+', '-', '*', '/'] のリスト
        """
        obj = cls(None, first_paren=first_paren, show_equal=show_equal)
        obj.expr_values = expr_values
        obj.operators = operators
        obj.total = total
        return obj

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def parse_expression(tokens):
        stack = []
        i = 0
        while i < len(tokens):
            t = tokens[i]
            if t in ('+', '-', r'\times', r'\div'):
                stack.append('*' if t == r'\times' else '/' if t == r'\div' else t)
            else:
                # 値
                stack.append(Problem.parse_single_value(t))
            i += 1
        return stack

    @classmethod
    def parse_latex_expr(cls, latex_str: str):
        tokens = cls.latex_tokenize(latex_str)
        expr_list = cls.parse_expression(tokens)

        # 値と演算子に分割
        expr_values = expr_list[::2]  # 偶数インデックス → 値
        operators = expr_list[1::2]   # 奇数インデックス → 演算子

        blocks, base_ops = build_blocks(expr_values, operators)
        total = evaluate_blocks(blocks, base_ops)
        return expr_values, operators, total


    def parse_text_expr(expr_text):
        """
        Textビューの式文字列から expr_values, operators, total を生成
        """
        # 末尾の = を除去
        expr_text = expr_text.rstrip().rstrip('=').rstrip()
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
        # total を計算
        total = expr_values[0]
        for op, val in zip(operators, expr_values[1:]):
            if op == '+':
                total += val
            elif op == '-':
                total -= val
            elif op == '*':
                total *= val
            elif op == '/':
                total /= val

        return expr_values, operators, total


# ------------------------------
# LaTeXRenderer
# 役割: PDF用に LaTeX 文書を生成
# 責任:
#     プリアンブル + 問題部の結合
#     PDF出力用の調整（\\displaystyle や \vfill）は Problem.to_latex_pdf() が担当
# ポイント: LaTeX 文書の「完成形」を作る
# ------------------------------
class LaTeXRenderer:
    PAPER_MAP = {
        'A3': 'a3paper',
        'A4': 'a4paper',
        'A5': 'a5paper',
        'B4': 'b4paper',
        'B5': 'b5paper'
    }

    def __init__(self, builder, settings):
        self.builder = builder
        self.settings = settings

    def render_pdf(self):
        paper = self.PAPER_MAP.get(self.settings['paper_size'], 'a4paper')
        cols = int(self.settings['cols'])
        num_problems = len(self.builder.problems)
        per_col = (num_problems + cols - 1) // cols
        landscape_opt = ',landscape' if self.settings['landscape'] else ''
        title = self.settings['title'] if self.settings['title_check'] else ''
        date = self.settings['date'] if self.settings['date_check'] else ''
        name = self.settings['name'] if self.settings['name_check'] else ''

        if self.settings['show_answer'] and self.settings['answer_pos'] == 'footer':
            answers = self.render_answers(self.builder.problems, per_col, show_answer=self.settings['show_answer'], answer_pos=self.settings['answer_pos'], footer_rotate=self.settings['footer_rotate'])
        else:
            answers = ''

        preamble = f"""
\\documentclass[{paper}, {self.settings['font_size']}{landscape_opt}]{{jarticle}}
\\usepackage[top={self.settings['margin_top']}mm,
            bottom={self.settings['margin_bottom']}mm,
            left={self.settings['margin_left']}mm,
            right={self.settings['margin_right']}mm]{{geometry}}
\\usepackage{{amsmath, amssymb, multicol, fancyhdr, enumerate, graphicx, array}}
\\pagestyle{{fancy}}
\\fancyhf{{}}
\\renewcommand{{\\footrulewidth}}{{0pt}}
\\fancyhead[L]{{{title}}}
\\fancyhead[C]{{{date}}}
\\fancyhead[R]{{{name}}}
{answers}
\\begin{{document}}
""".strip()
        problems = self.builder.build_block('latex_pdf')
        if self.settings['show_answer'] and self.settings['answer_pos'] == 'new_page':
            answers = self.render_answers(self.builder.problems, per_col, show_answer=self.settings['show_answer'], answer_pos=self.settings['answer_pos'])
        return preamble + problems + answers + r'\end{document}'

    def render_source(self):
        return self.builder.build_block('latex_source')

    # --- 解答表示用
    def render_answers(self, problems, cols, show_answer=False, answer_pos="new_page", footer_rotate=False):
        """
        problems: [(問題文字列, 解答文字列), ...]
        show_answer: bool, 解答を表示するか
        answer_pos: "new_page" または "footer"
        footer_rotate: bool, フッター回転180°
        """
        latex_code = ''

        # --- 解答表示 ---
        if show_answer:
            if answer_pos == "new_page":
                latex_code += "\\newpage\n"
                latex_code += self.builder.build_block('latex_pdf', show_answer=show_answer)
            elif answer_pos == "footer":
                # フッター用に (番号, 解答) リストを作る
                answers_list = [(i+1, prob.total) for i, prob in enumerate(problems)]
                latex_code += self.make_footer_answers(answers_list, cols, rotate=footer_rotate)

        return latex_code

    # --- フッターの解答表示用
    def make_footer_answers(self, answers, cols=None, rotate=False):
        """
        answers: [(番号, 解答), ...] のリスト
        cols: 1行に表示する列数
        rotate: Trueなら180°回転
        """
        num_problems = len(answers)
        rows = (num_problems + cols - 1) // cols  # 切り上げ

        lines = []
        for r in range(rows):
            chunk = answers[r*cols : (r+1)*cols]
            # 不足分は空文字で埋める
            while len(chunk) < cols:
                chunk.append(("", ""))
            row = " & ".join([f"({n})\\ {ans}" if n != "" else "" for n, ans in chunk])
            lines.append(row + r" \\")
        table_body = "\n".join(lines)
        tex = r"\fancyfoot[R]{%" "\n"
        tex += r"\begin{scriptsize}" "\n"
        if rotate:
            tex += r"\rotatebox[origin=l]{180}{%" "\n"
        tex += rf"$\begin{{array}}{{*{{{cols}}}{{Wl{{3.5em}}}}}}" "\n"
        tex += table_body + "\n"
        tex += r"\end{array}$" "\n"
        if rotate:
            tex += r"}" "\n"
        tex += r"\end{scriptsize}" "\n"
        tex += r"}" "\n"

        return tex


# ------------------------------
# TextRenderer
# 役割: Textビュー用の表示
# 責任: BlockBuilder を使ってテキスト形式で整形
# ポイント: ビュー表示専用、PDF生成とは分離
# ------------------------------
class TextRenderer:
    def __init__(self, builder):
        self.builder = builder

    def render(self):
        header = f"[改行: {self.builder.settings.get('cols', 1)}]"
        body = self.builder.build_block('text')
        return header + '\n' + body


# ------------------------------
# LaTeX2PDF
# ------------------------------
class LaTeX2PDF:
    def __init__(self, latex_str: str, settings=None, cleanup=True):
        self.settings = settings
        # 出力先ディレクトリを settings から取得
        self.output_dir = settings.get('dir_name', '.') if settings else '.'
        os.makedirs(self.output_dir, exist_ok=True)
        self.cleanup = cleanup    # True なら中間ファイルを削除
        self.latex_str = latex_str
        
    @classmethod
    def from_latex(cls, latex_str, settings=None):
        """LaTeX文字列から直接インスタンス生成"""
        return cls(latex_str, settings)

    def _cleanup_intermediate(self, filename: str):
        """PDF生成後に関連する中間ファイルを削除"""
        base_path = os.path.join(self.output_dir, filename)
        exts = ['.aux', '.log', '.out', '.toc', '.dvi']
        for ext in exts:
            path = base_path + ext
            if os.path.exists(path):
                os.remove(path)

    def compile_pdf(self, filename='output'):
        # tex_path = os.path.join(self.output_dir, f'{filename}.tex')
        # pdf_path = os.path.join(self.output_dir, f'{filename}.pdf')
        tex_path = f'{filename}.tex'
        pdf_path = f'{filename}.pdf'

        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(self.latex_str)
        try:
            subprocess.run(['platex', '-interaction=nonstopmode', tex_path], check=True, cwd=self.output_dir)
            subprocess.run(['dvipdfmx', tex_path.replace('.tex', '.dvi')], check=True, cwd=self.output_dir)

            # 中間ファイル削除
            if self.cleanup:
                self._cleanup_intermediate(filename)
        
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'LaTeXコンパイルエラー: {e}')

        return pdf_path


# ---------- utils ----------
def expr_to_latex(expr_str: str) -> str:
    """
    プレーンな式文字列を LaTeX に変換する
    """
    parts = expr_str.split()
    converted = []

    for p in parts:
        if p.lstrip('-').isdigit():
            converted.append(paren_if_negative(int(p)))
        elif p in ('+', '-', '*', '/'):
            if p == '*':
                converted.append(r'\times')
            elif p == '/':
                converted.append(r'\div')
            else:
                converted.append(p)
        else:
            converted.append(p)

    return ' '.join(converted)

def problem_to_latex(problem: Problem) -> str:
    return f"${expr_to_latex(problem.expr)} =$"

def answer_to_latex(problem: Problem) -> str:
    return f"${expr_to_latex(problem.expr)} = {problem.answer}$"
