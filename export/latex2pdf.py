import os
import subprocess


# ------------------------------
# LaTeX2PDF
# ------------------------------
class LaTeX2PDF:
    def __init__(self, latex_str: str, settings=None, cleanup=True):
        self.settings = settings
        # 出力先ディレクトリを settings から取得
        self.output_dir = self.settings.get('dir_name', '~/Documents/LaTeXOutput') if settings else '~/Documents/LaTeXOutput'
        output_dir = os.path.expanduser(self.output_dir)
        os.makedirs(output_dir, exist_ok=True)
        self.cleanup = cleanup    # True なら中間ファイルを削除
        self.latex_str = latex_str
        
    @classmethod
    def from_latex(cls, latex_str, settings=None):
        """LaTeX文字列から直接インスタンス生成"""
        return cls(latex_str, settings)

    def _cleanup_intermediate(self, filename: str):
        """PDF生成後に関連する中間ファイルを削除"""
        output_dir = os.path.expanduser(self.output_dir)
        base_path = os.path.join(output_dir, filename)
        exts = ['.aux', '.log', '.out', '.toc', '.dvi']
        for ext in exts:
            path = base_path + ext
            if os.path.exists(path):
                os.remove(path)

    def compile_pdf(self, filename='output'):
        output_dir = os.path.expanduser(self.output_dir)
        tex_path = os.path.join(output_dir, f'{filename}.tex')
        pdf_path = os.path.join(output_dir, f'{filename}.pdf')

        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(self.latex_str)
        try:
            subprocess.run(['platex', '-interaction=nonstopmode', f'{filename}.tex'], check=True, cwd=output_dir)
            subprocess.run(['dvipdfmx', f'{filename}.dvi'], check=True, cwd=output_dir)

            # 中間ファイル削除
            if self.cleanup:
                self._cleanup_intermediate(filename)
        
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'LaTeXコンパイルエラー: {e}')

        return pdf_path
