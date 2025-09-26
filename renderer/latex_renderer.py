# ------------------------------
# LaTeXRenderer
# 役割: PDF用に LaTeX 文書を生成
# 責任:
#     プリアンブル + 問題部の結合
#     PDF出力用の調整（\\displaystyle や \vfill）は Problem.to_latex_pdf() が担当
# ポイント: LaTeX 文書の「完成形」を作る
# ------------------------------

MACRO = r'''
\let\orifrac = \frac
\def\frac#1#2{\orifrac{\mkern1mu #1\mkern1mu }{\mkern1mu #2\mkern1mu}}
'''

class LaTeXRenderer:
    PAPER_MAP = {
        'A3': 'a3paper',
        'A4': 'a4paper',
        'A5': 'a5paper',
        'B4': 'b4paper',
        'B5': 'b5paper'
    }

    def __init__(self, problems, settings):
        self.problems = problems
        self.settings = settings

    def build_block(self, mode='latex_pdf', show_answer=False, boxed=True) -> str:
        """mode: 'latex_pdf' | 'latex_source' | 'text'"""
        num_problems = len(self.problems)
        cols = int(self.settings['cols'])
        per_col = (num_problems + cols - 1) // cols

        problems = []
        for i, p in enumerate(self.problems, start=1):
            if mode == 'latex_pdf':
                problems.append(p.to_latex_pdf(show_answer, boxed))
            elif mode == 'latex_source':
                problems.append(p.to_latex_source())
            else:
                raise ValueError(f'Unknown mode {mode}')

            if i % per_col == 0 and i < num_problems:
                problems.append(r'\null\columnbreak')


            if i == num_problems:
                problems.append(r'\null')

        return rf"""
\begin{{multicols*}}{{{cols}}}
\begin{{enumerate}}[(1)]
{chr(10).join(problems)}
\end{{enumerate}}
\end{{multicols*}}
""".strip()

    def render_latex(self):
        paper = self.PAPER_MAP.get(self.settings['paper_size'], 'a4paper')
        cols = int(self.settings['cols'])
        num_problems = len(self.problems)
        per_col = (num_problems + cols - 1) // cols
        landscape_opt = ',landscape' if self.settings['landscape'] else ''
        title = self.settings['title'] if self.settings['use_title'] else ''
        date = self.settings['date'] if self.settings['use_date'] else ''
        name = self.settings['name'] if self.settings['use_name'] else ''
        

        if self.settings['show_answer'] and self.settings['answer_pos'] == 'footer':
            answers = self.render_answers(self.problems, per_col, show_answer=self.settings['show_answer'], answer_pos=self.settings['answer_pos'], footer_rotate=self.settings['footer_rotate'])
        else:
            answers = ''
        preamble =''
        preamble += f"% TYPE={self.settings['prob_type']}\n"
        if self.settings['prob_type'] == 'expand':
            preamble += f"% VAR_TYPE={self.settings['var_type']}\n"
            preamble += f"% VAR_SET={self.settings['var_set']}\n"
        if self.settings['use_seed']:
            preamble += f"% SEED={self.settings['seed']}\n"
        preamble += f"""
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
{MACRO}
\\begin{{document}}
""".strip()
        problems = self.build_block('latex_pdf')
        if self.settings['show_answer'] and self.settings['answer_pos'] == 'new_page':
            answers = self.render_answers(self.problems, per_col, show_answer=self.settings['show_answer'], answer_pos=self.settings['answer_pos'], boxed=self.settings['boxed'])
        return preamble + problems + answers + r'\end{document}'

    def render_source(self):
        return self.build_block('latex_source')

    # --- 解答表示用
    def render_answers(self, problems, cols, show_answer=False, answer_pos="new_page", boxed=True, footer_rotate=False):
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
                latex_code += self.build_block('latex_pdf', show_answer=show_answer, boxed=boxed)
            elif answer_pos == "footer":
                # フッター用に (番号, 解答) リストを作る
                answers_list = [(i+1, prob.solve) for i, prob in enumerate(problems)]
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

def problem_to_latex(problem) -> str:
    return f"${expr_to_latex(problem.expr)} =$"

def answer_to_latex(problem) -> str:
    return f"${expr_to_latex(problem.expr)} = {problem.answer}$"
