from utils.utils import paren_if_negative


class ProblemBase:
    def __init__(self, data, settings):
        """
        expr_values : List[int|Fraction]  数値のまま保持
        operators   : List[str]            '+','-','*','/' など
        show_equal  : bool
        """
        self.data = data
        self.solve = data.get('solve', 0)
        self.first_paren = settings['first_paren']
        self.show_equal = settings['show_equal']
        self.line_break = settings['line_break']

    # --- Textビュー用 --- #
    def to_text(self) -> str:
        raise NotImplementedError

    # --- LaTeXビュー用 --- #
    def to_latex_source(self) -> str:
        latex = self._format_latex(pdf_mode=False)
        return rf'\item ${latex}$'

    # --- PDF出力用 --- #
    def to_latex_pdf(self, show_answer=False, boxed=True) -> str:
        latex = self._format_latex(pdf_mode=True, show_answer=show_answer, boxed=boxed)
        return rf'\item $\displaystyle {latex}$\vfill'

    @classmethod
    def from_values(cls, data, settings):
        obj = cls(data, settings)
        return obj
