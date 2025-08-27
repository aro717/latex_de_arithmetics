import os
import subprocess
import re
from fractions import Fraction
from core.problem_generator import RawFraction
from utils import number_to_latex, text_to_latex


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

    def build_block(self, mode='text_pdf') -> str:
        """mode: 'latex_pdf' | 'latex_source' | 'text'"""
        num_problems = len(self.problems)
        cols = int(self.settings['cols'])
        per_col = (num_problems + cols - 1) // cols

        problems = []
        for i, p in enumerate(self.problems, start=1):
            if mode == 'latex_pdf':
                problems.append(p.to_latex_pdf())
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
    def __init__(self, expr, show_equal=True):
        self.expr = expr # 元の式文字列、例: '1/2', '1*2'
        self.show_equal = show_equal

    def _format_latex(self, pdf_mode: bool = False) -> str:
        """符号や分数、演算子を LaTeX 用に整形"""
        latex = str(self.expr)

        # show_equalがTrueなら末尾に「=」を付ける
        if self.show_equal:
            latex = latex.rstrip()  # 念のため空白除去
            if not latex.endswith('='):
                latex += ' ='

        # 括弧変換 (PDF時のみ \left/\right)
        if pdf_mode:
            latex = latex.replace('(', r'\left(').replace(')', r'\right)')

        # 演算子変換
        latex = latex.replace('*', r'\times').replace('/', r'\div')

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
        text = self.expr
        # 演算子変換
        text = text.replace('*', '×').replace('/', '÷')
        # LaTeX形式の分数 \frac{a}{b} は 'a/b' に
        text = re.sub(r'\\frac\{(\d+)\}\{(\d+)\}', r'\1/\2', text)
        # show_equalがTrueなら末尾に「=」を付ける
        if self.show_equal:
            text = text.rstrip()  # 念のため空白除去
            if not text.endswith('='):
                text += ' ='
        return text

    # --- LaTeXビュー用 ---#
    def to_latex_source(self) -> str:
        latex = self._format_latex(pdf_mode=False)
        return rf'\item ${latex}$'

    # --- PDF出力用 ---#
    def to_latex_pdf(self) -> str:
        latex = self._format_latex(pdf_mode=True)
        return rf'\item $\displaystyle {latex}$\vfill'


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

        preamble = f"""
\\documentclass[{paper}, {self.settings['font_size']}{landscape_opt}]{{jarticle}}
\\usepackage[top={self.settings['margin_top']}mm,
            bottom={self.settings['margin_bottom']}mm,
            left={self.settings['margin_left']}mm,
            right={self.settings['margin_right']}mm]{{geometry}}
\\usepackage{{amsmath, amssymb, multicol, fancyhdr, enumerate}}
\\pagestyle{{fancy}}
\\fancyhf{{}}
\\lhead{{{self.settings['title']}}}
\\chead{{{self.settings['date']}}}
\\rhead{{{self.settings['name']}}}
\\begin{{document}}
""".strip()
        problems = self.builder.build_block('latex_pdf')
        return preamble + problems + r'\end{document}'

    def render_source(self):
        return self.builder.build_block('latex_source')


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
        header = f'[改行: {self.builder.settings.get('cols', 1)}]'
        body = self.builder.build_block('text')
        return header + '\n' + body


# ------------------------------
# LaTeX2PDF
# ------------------------------
class LaTeX2PDF:
    def __init__(self, latex_str: str, settings=None, cleanup=True):
        self.settings = settings
        # 出力先ディレクトリを settings から取得
        self.output_dir = settings.get('last_output_dir', '.') if settings else '.'
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
        tex_path = os.path.join(self.output_dir, f'{filename}.tex')
        pdf_path = os.path.join(self.output_dir, f'{filename}.pdf')

        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(self.latex_str)
        try:
            subprocess.run(['platex', tex_path], check=True)
            subprocess.run(['dvipdfmx', tex_path.replace('.tex', '.dvi')], check=True)

            # 中間ファイル削除
            if self.cleanup:
                self._cleanup_intermediate(filename)
        
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'LaTeXコンパイルエラー: {e}')

        return pdf_path
