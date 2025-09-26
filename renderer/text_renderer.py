# ------------------------------
# TextRenderer
# 役割: Textビュー用の表示
# 責任: BlockBuilder を使ってテキスト形式で整形
# ポイント: ビュー表示専用、PDF生成とは分離
# ------------------------------
class TextRenderer:
    def __init__(self, problems, settings):
        self.problems = problems
        self.settings = settings

    def render(self):
        header = f"[改行: {self.settings.get('cols', 1)}]"
        body = self.build_block()
        return header + '\n' + body

    def build_block(self) -> str:
        num_problems = len(self.problems)
        cols = int(self.settings['cols'])
        per_col = (num_problems + cols - 1) // cols

        problems = []
        for i, p in enumerate(self.problems, start=1):
            problems.append(f'({i}) {p.to_text()}')

            if i % per_col == 0 and i < num_problems:
                 problems.append('[改段]')

        return '\n'.join(problems)
