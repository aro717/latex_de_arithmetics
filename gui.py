import re
import FreeSimpleGUI as sg
import json
import os
from datetime import datetime
from collections import Counter
from itertools import zip_longest
from settings import load_settings, save_settings
from core.problem_generator import generate_problem_set
from core.latex_generator import BlockBuilder, Problem, LaTeXRenderer, TextRenderer, LaTeX2PDF
from utils import max_2terms


class SettingsManager:
    """settings の適用・収集・検証を担当（GUIから分離）"""
    def __init__(self, settings, window):
        self.settings = settings
        self.window = window
        self.validation_rules = {}

    # --- 適用 ---
    def apply_to_gui(self):
        s = self.settings
        # ヘッダ表示
        if s['title_check']:
            self.window['-IN_TITLE-'].update(visible=True)
        if s['date_check']:
            self.window['-IN_DATE-'].update(visible=True)
        if s['name_check']:
            self.window['-IN_NAME-'].update(visible=True)
        # ドメイン別の有効/無効
        domain = s['domain']
        if domain == 'Z':
            self.window['-FIRST_PAREN-'].update(disabled=False)
        elif domain == 'Q':
            self.window['-FIRST_PAREN-'].update(disabled=False)
            for k in ['-QFRAC-','-IRREDUCIBLE-','-QDEC-','-DECIMAL_PLACES-']:
                self.window[k].update(disabled=False)

    # --- 収集 ---
    def collect_from_values(self, values, arith_ops_dict):
        s = self.settings
        s['file_name'] = values['-FILE_NAME-']
        s['paper_size'] = values['-PAPER-']
        s['font_size'] = values['-FONTSIZE-']
        s['margin_top'] = int(values['-MTOP-'])
        s['margin_bottom'] = int(values['-MBOTTOM-'])
        s['margin_left'] = int(values['-MLEFT-'])
        s['margin_right'] = int(values['-MRIGHT-'])
        s['landscape'] = values['-CHK_LANDSCAPE-']
        s['title_check'] = values['-CHK_TITLE-']
        s['title'] = values['-IN_TITLE-'] if values['-CHK_TITLE-'] else ''
        s['date_check'] = values['-CHK_DATE-']
        s['date'] = values['-IN_DATE-'] if values['-CHK_DATE-'] else ''
        s['name_check'] = values['-CHK_NAME-']
        s['name'] = values.get('-IN_NAME-') if values['-CHK_NAME-'] else ''
        s['num_problems'] = int(values['-NPROBLEMS-'])
        s['cols'] = int(values['-NCOLS-'])
        s['n_terms'] = int(values.get('-NTERMS-', 2))
        s['domain'] = next(label for label in ['N','Z','Q'] if values.get(f'-DOMAIN_{label}-'))
        s['allow_zero'] = values['-ALLOW_ZERO-']
        s['allow_dup'] = values['-ALLOW_DUP-']
        s['show_equal'] = values['-SHOW_EQUAL-']
        s['ops'] = { '+': values['-ADD-'], '-': values['-SUB-'], '*': values['-MUL-'], '/': values['-DIV-'] }
        s['first_paren'] = values['-FIRST_PAREN-']
        s['q_repr'] = 'frac' if values['-QFRAC-'] else 'decimal'
        s['irreducible'] = values['-IRREDUCIBLE-']
        s['decimal_places'] = values['-DECIMAL_PLACES-']
        s['min_val'] = values['-MIN-']
        s['max_val'] = values['-MAX-']
        s['show_answer'] = values['-SHOW_ANSWER-']
        s['answer_pos'] = 'new_page' if values['-ANS_NEW_PAGE-'] else 'footer'
        s['footer_rotate'] = values['-FOOTER_ROTATE-']
        return s

    # --- バリデーション定義/実行 ---
    def set_validation_rules(self, rules):
        self.validation_rules = rules

    def validate(self, values):
        errors = []
        for key, rules in self.validation_rules.items():
            for func, msg in rules:
                # 値渡し/全体渡しの切り替え
                if key in ('-ARITH_OPS-', '-NPROBLEMS-'):
                    if not func(values):
                        errors.append(msg)
                elif key in values:
                    if not func(values[key]):
                        errors.append(msg)
        return errors


class TextSyncService:
    """Textビュー ↔ Problems 同期、差分/重複チェック、LaTeX抽出など"""
    @staticmethod
    def cleaned_lines(text: str):
        cleaned = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if '[改段]' in line or '[改行:' in line:
                continue
            line = re.sub(r'^\(\d+\)\s*', '', line)  # (1) を除去
            cleaned.append(line)
        return cleaned

    @staticmethod
    def diff_and_dup(current_text_list, edited_list):
        from collections import Counter
        from itertools import zip_longest
        diff = []
        for i, (old, new) in enumerate(zip_longest(current_text_list, edited_list, fillvalue="")):
            if old != new:
                diff.append(f'({i+1}) {old} -> {new}')
        counts = Counter(edited_list)
        dup = [f'({i+1}) {p}' for i, p in enumerate(edited_list) if counts[p] > 1]
        return diff, dup

    @staticmethod
    def extract_items_from_tex(tex: str) -> list[str]:
        matches = re.findall(r'\\item\s*(?:\$([^$]+)\$|(.+))', tex)
        problems = []
        for m in matches:
            expr = m[0] if m[0] else m[1]
            problems.append(expr.strip())
        return problems


class ViewBuilder:
    def __init__(self, settings):
        self.settings = settings
        self.link_map = {
            '-CHK_TITLE-': ['-IN_TITLE-'],
            '-CHK_DATE-': ['-IN_DATE-', '-BTN_DATE-'],
            '-CHK_NAME-': ['-IN_NAME-']
        }

    def build(self):
        s = self.settings
        # --- ドキュメント設定 ---
        doc_frame = sg.Frame('ドキュメント設定', [
            [sg.Text('ファイル名:'), sg.InputText(default_text=s['file_name'], key='-FILE_NAME-', size=(30, 1))],
            [sg.Text('用紙サイズ:'), sg.Combo(['A3','A4','A5','B4','B5'], default_value=s['paper_size'], key='-PAPER-'),
             sg.Checkbox('横向き', key='-CHK_LANDSCAPE-', default=s['landscape']),
             sg.Text('フォントサイズ:'), sg.Combo(['10pt','11pt','12pt'], key='-FONTSIZE-', default_value=s['font_size'])],
            [sg.Text('余白(mm): 上'), sg.InputText(str(s['margin_top']), size=(4, 1), key='-MTOP-'),
             sg.Text('下'), sg.InputText(str(s['margin_bottom']), size=(4, 1), key='-MBOTTOM-'),
             sg.Text('左'), sg.InputText(str(s['margin_left']), size=(4, 1), key='-MLEFT-'),
             sg.Text('右'), sg.InputText(str(s['margin_right']), size=(4, 1), key='-MRIGHT-')]
        ], size=(500, 100))

        # --- ヘッダ設定 ---
        header_frame = sg.Frame('ヘッダ設定', [
            [sg.Checkbox('表題', key='-CHK_TITLE-', default=s['title_check'], enable_events=True),
             sg.InputText(default_text=s['title'], key='-IN_TITLE-', visible=False, size=(30, 1))],
            [sg.Checkbox('日付', key='-CHK_DATE-', default=s['date_check'], enable_events=True),
             sg.InputText(default_text=s['date'], key='-IN_DATE-', visible=False, size=(12, 1)),
             sg.CalendarButton('選択', target='-IN_DATE-', format='%Y/%m/%d', visible=False, key='-BTN_DATE-', size=(10,1), pad=(0,0))],
            [sg.Checkbox('氏名', key='-CHK_NAME-', default=s['name_check'], enable_events=True),
             sg.InputText(default_text=s['name'], key='-IN_NAME-', visible=False, size=(30, 1))],
        ], size=(500, 110))

        # --- 本文設定 ---
        # 四則演算ラベル
        self.ops_dict = {'+': '+算', '-': '−算', '*': '×算', '/': '÷算'}
        self.arith_ops_dict = {
            '-ADD-': '+',
            '-SUB-': '-',
            '-MUL-': '*',
            '-DIV-': '/'
        }
        self.ops_keys = list(self.arith_ops_dict.keys())
        arith_ops_row = [sg.Checkbox(self.ops_dict[op], key=k, default=self.settings['ops'][op]) for k, op in self.arith_ops_dict.items()]

        # self.domain_options = ['N', 'Z', 'Q', 'R', 'C']
        self.domain_options = ['N', 'Z', 'Q']
        domain_row = [sg.Text('領域:')]
        for label in self.domain_options:
            domain_row.append(sg.Radio(label, 'DOMAIN', key=f'-DOMAIN_{label}-', default=(label==self.settings['domain']), enable_events=True))
        
        # オプション
        domain_options = [sg.Frame('オプション', [
            [sg.Checkbox('先頭の括弧', key='-FIRST_PAREN-', default=self.settings['first_paren'], disabled=True)],
            [sg.Radio('分数', 'QREP', key='-QFRAC-', default=self.settings['frac'], enable_events=True, disabled=True),
             sg.Checkbox('既約', key='-IRREDUCIBLE-', default=self.settings['irreducible'], disabled=True),
             sg.Radio('小数', 'QREP', key='-QDEC-', default=self.settings['decimal'], enable_events=True, disabled=True),
             sg.Text('小数点以下:'), sg.Spin([i for i in range(1,6)], initial_value=self.settings['decimal_places'], key='-DECIMAL_PLACES-', disabled=True)
            ]
          ], pad=(30,0))
        ]

        # 0の有無ラベル
        allow_zero_row = [sg.Checkbox('乱数に0を許容', key='-ALLOW_ZERO-', default=self.settings['allow_zero'])]

        # 項数ラベル
        terms_row = [
            sg.Text('項数:'),
            sg.Combo([2, 3, 4], default_value=self.settings['n_terms'], key='-NTERMS-', enable_events=True),
            sg.Text('R×R -> R', key='-NTERMS_DISP-', text_color='blue')
        ]

        # タブ1: 四則演算
        tab_arith = [
            [sg.Text('問題数:'), sg.InputText(str(self.settings['num_problems']), size=(5, 1), key='-NPROBLEMS-'),
             sg.Text('列数:'), sg.InputText(str(self.settings['cols']), size=(5, 1), key='-NCOLS-')],
            arith_ops_row,
            domain_row,
            domain_options,
            allow_zero_row,
            terms_row,
            [sg.Text('乱数 最小値:'), sg.InputText(default_text=self.settings['min_val'], size=(5, 1), key='-MIN-'),
             sg.Text('最大値:'), sg.InputText(default_text=self.settings['max_val'], size=(5, 1), key='-MAX-')],
            [sg.Checkbox('重複許可', key='-ALLOW_DUP-', default=self.settings['allow_dup']),
             sg.Checkbox('= を表示', key='-SHOW_EQUAL-', default=self.settings['show_equal'])],
            [sg.Checkbox("解答表示", key="-SHOW_ANSWER-", enable_events=True),
                sg.Text("場所:"),
                sg.Radio("新規ページ", "ANSWER_POS", key="-ANS_NEW_PAGE-", enable_events=True, default=True, disabled=True),
                sg.Radio("フッター", "ANSWER_POS", key="-ANS_FOOTER-", enable_events=True, disabled=True),
                sg.Checkbox('回転', key='-FOOTER_ROTATE-', disabled=True)
            ]
        ]

        # タブ2: 展開
        tab_expand = [
            [sg.Text('多項式の数:'), sg.InputText(default_text=self.settings['poly_num'], size=(5, 1), key='-POLY_NUM-')]
        ]

        tab_group = sg.TabGroup([
            [
            sg.Tab('四則演算', tab_arith, key='-TAB_ARITH-'),
             # sg.Tab('展開', tab_expand, key='-TAB_EXPAND-')
             ]
        ], key='-TAB_GROUP-', size=(480, 300), pad=(10,5))

        execution_buttons = [
            sg.Button('LaTeX生成', key='-GEN_LATEX-'),
            sg.Button('LaTeX読込', key='-LOAD_LATEX-'),
            sg.Button('', key='-UPDATE_LATEX-', size=(8,1), disabled=True), # LaTeX更新
            sg.Button('PDF生成', key='-GEN_PDF-', size=(8,1)),
            sg.Button('終了')
        ]

        body_frame = sg.Frame('本文設定', [[tab_group]], size=(500, 340))

        left_col = sg.Column([
            [doc_frame],
            [header_frame],
            [body_frame],
            [sg.Multiline('', key='-LOG-', size=(60, 10),
                text_color='white', background_color='black',
                autoscroll=True, disabled=True)]
        #   [sg.Button('LaTeX生成', key='-GEN_LATEX-'), sg.Button('PDF生成', key='-GEN_PDF-'), sg.Button('終了')]
        ], vertical_alignment='top')

        right_col = sg.Column([
            [sg.TabGroup([
                [sg.Tab('LaTeXビュー', [
                    [sg.Multiline('', size=(60, 40), key='-LATEX_VIEW-', autoscroll=True, disabled=True)]
                ])],
                [sg.Tab('Textビュー', [
                    [sg.Multiline('', size=(60, 40), key='-TEXT_VIEW-', autoscroll=True, disabled=True, enable_events=True)]
                ])]
            ], key='-TAB_VIEW-')],
            execution_buttons,
        ], vertical_alignment='top')

        layout = [[left_col, right_col]]

        # self.window = sg.Window('LaTeX de Arithmetics', layout, finalize=True)
        return layout


class MyApp:
    def __init__(self):
        self.settings = load_settings()
        if self.settings.get('date_check', False) and not self.settings.get('date'):
            self.settings['date'] = datetime.today().strftime('%Y/%m/%d')

        # 四則演算マップ（これだけMyAppで管理）
        self.ops_dict = {'+': '+算', '-': '−算', '*': '×算', '/': '÷算'}
        self.arith_ops_dict = {'-ADD-': '+', '-SUB-': '-', '-MUL-': '*', '-DIV-': '/'}
        self.domain_options = ['N', 'Z', 'Q']

        # --- View ---
        self.view = ViewBuilder(self.settings)
        self.window = sg.Window('LaTeX de Arithmetics', self._build_layout(), finalize=True)
        self.link_map = self._link_map()  # 既存の link_map を返す小ヘルパーでもOK

        # --- Services ---
        self.settings_mgr = SettingsManager(self.settings, self.window)
        self.sync = TextSyncService()

        # 問題モデル
        self.problems = []

        # 差分状態のフラグ
        self._text_changed_diff = False

        # 適用
        self.settings_mgr.apply_to_gui()
        self._bind_validation_rules()

    # ---------- Layout ----------
    def _build_layout(self):
        # レイアウト構築を ViewBuilder に一任
        return self.view.build()

    def _link_map(self):
        return {
          '-CHK_TITLE-': ['-IN_TITLE-'],
          '-CHK_DATE-': ['-IN_DATE-', '-BTN_DATE-'],
          '-CHK_NAME-': ['-IN_NAME-']
        }

    # ---------- Validation ----------
    def _bind_validation_rules(self):
        # ★ここで「辞書キー重複」を解消して一箇所に集約
        # 既存の not_empty / is_integer / is_valid_date / at_least_one_selected / validate_num_problems を使う
        rules = {
            '-IN_TITLE-': [
              (lambda v: (not self.window['-CHK_TITLE-'].get()) or len(v) > 0, "表題を入力してください")
            ],
            '-IN_DATE-': [
              (lambda v: (not self.window['-CHK_DATE-'].get()) or self.not_empty(v), "日付を入力してください"),
              (lambda v: (not self.window['-CHK_DATE-'].get()) or self.is_valid_date(v), '日付はYYYY/MM/DD形式で正しく入力してください')
            ],
            '-NCOLS-': [
              (self.is_integer, '列数は整数で入力してください')
            ],
            '-POLY_NUM-': [
              (self.is_integer, '多項式の数は整数で入力してください')
            ],
            '-ARITH_OPS-': [
              (lambda vals: self.at_least_one_selected(vals, self.arith_ops_dict.keys()), '演算を少なくとも1つ選択してください')
            ],
            # 生成可能数チェックは別キー名にする方が辞書重複回避できて安全
            '-NPROBLEMS-': [
              (lambda vals: self.validate_num_problems(vals), '生成可能なユニーク問題数を超えています')
            ]
        }
        self.settings_mgr.set_validation_rules(rules)

    # ---------- Run Loop ----------
    def run(self):
        handler = {
            '-GEN_LATEX-': self._on_generate_clicked,
            '-UPDATE_LATEX-': self._on_update_latex_clicked,
            '-LOAD_LATEX-': self._on_load_latex_clicked,
            '-GEN_PDF-': self._on_generate_pdf_clicked,
        }
        while True:
            event, values = self.window.read(timeout=100) # timeoutでポーリング
            if event in (sg.WINDOW_CLOSED, '終了'):
                break

            # 共通：チェックボックス可視切替
            if event in self.link_map:
                self._on_toggle_input(event, values[event])

            if event == '-SHOW_ANSWER-':
                self._on_show_answer_toggle(values)
            if event in [f'-ANS_{label}-' for label in ['NEW_PAGE', 'FOOTER']]:
                self._on_footer_opt_toggle(values)

            # 入力系イベント
            if event == '-NTERMS-':
                self._on_nterms_changed(values)
            if event in [f'-DOMAIN_{label}-' for label in self.domain_options]:
                self._on_domain_changed(values)
            if event in ['-QFRAC-', '-QDEC-']:
                self._on_qrepr_changed(event)

            # Textビューの編集検知
            if event == '-TEXT_VIEW-':
                self._on_text_changed()

            # ボタン類
            if event in handler:
                handler[event](values)

        self.window.close()

    # ---------- Handlers ----------
    def _on_generate_clicked(self, values):
        errs = self.settings_mgr.validate(values)
        if errs: return self.log('\n'.join(errs), error=True)

        self.settings_mgr.collect_from_values(values, self.arith_ops_dict)
        # Problem作成
        self.problems = [Problem(data, first_paren=self.settings.get('first_paren', False), show_equal=self.settings.get('show_equal', True))
                         for data in generate_problem_set(self.settings)]
        self._render_all_views()
        self.log('問題生成 + ビュー更新完了')

    def _on_update_latex_clicked(self, _values):
        raw_text = self.window['-TEXT_VIEW-'].get()

        # --- 全角数字を半角に変換 ---
        def zenkaku_to_hankaku(s: str) -> str:
            return s.translate(str.maketrans(
                '０１２３４５６７８９',
                '0123456789'
            ))
        converted_text = zenkaku_to_hankaku(raw_text)
        # --- 警告表示 (変換があった場合) ---
        if raw_text != converted_text:
            self.log('※全角数字を半角に変換しました', error=True)
            self.window['-TEXT_VIEW-'].update(converted_text)

        edited = TextSyncService.cleaned_lines(converted_text)
        current = [p.to_text() for p in self.problems]
        diff, dup = TextSyncService.diff_and_dup(current, edited)
        if not diff and (self.settings.get('allow_dup', True) or not dup):
            return
        msg = '変更確認\n' + '\n'.join(diff)
        if not self.settings['allow_dup'] and dup:
            msg += '\n※重複あり\n' + '\n'.join(dup)
        if sg.popup_ok_cancel(msg, keep_on_top=True) != 'OK':
            return

        new_problems = []
        for i, expr_text in enumerate(edited):
            expr_values, operators, total = Problem.parse_text_expr(expr_text)
            if i < len(self.problems):
                problem = self.problems[i].from_values(expr_values, operators, total, first_paren=self.settings.get('first_paren', False), show_equal=True)
            else:
                problem = Problem.from_values(expr_values, operators, total, first_paren=self.settings.get('first_paren', False), show_equal=False)
            new_problems.append(problem)
        self.problems = new_problems

        self._render_all_views(latex_only=True)
        self.window['-UPDATE_LATEX-'].update('', disabled=True)
        self.window['-GEN_PDF-'].update('PDF生成', disabled=False)
        self.log('LaTeX更新完了')

    def _on_load_latex_clicked(self, _values):
        filename = sg.popup_get_file("TeXファイルを選択してください")
        if not filename: return
        with open(filename, encoding="utf-8") as f:
            tex_content = f.read()

        problem_strs = TextSyncService.extract_items_from_tex(tex_content)
        new_problems = []
        for i, expr_latex in enumerate(problem_strs):
            expr_values, operators, total = Problem.parse_latex_expr(expr_latex)
            problem = Problem.from_values(expr_values, operators, total, first_paren=self.settings.get('first_paren', False), show_equal=False)
            new_problems.append(problem)
        self.problems = new_problems
        
        self._render_all_views()
        self.log('LaTeX読込完了')

    def _on_generate_pdf_clicked(self, values):
        filename = values['-FILE_NAME-'].strip() or sg.popup_get_text('ファイル名を入力してください')
        if not filename: return
        builder = BlockBuilder(self.problems, self.settings)
        latex_renderer = LaTeXRenderer(builder, self.settings)
        latex_str = latex_renderer.render_pdf()
        pdf_gen = LaTeX2PDF.from_latex(latex_str, self.settings)
        pdf_path = pdf_gen.compile_pdf(filename)
        save_settings(self.settings)
        self.log(f'PDF生成完了: {pdf_path}')

    def _on_text_changed(self):
        current_text = self.window['-TEXT_VIEW-'].get()
        current_lines = TextSyncService.cleaned_lines(current_text)
        original_lines = [p.to_text() for p in self.problems]
        diff, dup = TextSyncService.diff_and_dup(original_lines, current_lines)

        # 差分状態が前回と変わったときだけUI更新
        if diff != self._text_changed_diff:
            self._text_changed_diff = diff
            if diff:
                self.window['-UPDATE_LATEX-'].update('LaTeX更新', disabled=False)
                self.window['-GEN_PDF-'].update('', disabled=True)
            else:
                self.window['-UPDATE_LATEX-'].update('', disabled=True)
                self.window['-GEN_PDF-'].update('PDF生成', disabled=False)

    def _on_domain_changed(self, values):
        selected = next((label for label in self.domain_options if values.get(f'-DOMAIN_{label}-')), 'N')
        if selected in ['N', 'R', 'C']:
            for k in ['-FIRST_PAREN-', '-QFRAC-','-IRREDUCIBLE-','-QDEC-','-DECIMAL_PLACES-']:
                self.window[k].update(disabled=True)
        if selected == 'Z':
            self.window['-FIRST_PAREN-'].update(disabled=False)
            for k in ['-QFRAC-','-IRREDUCIBLE-','-QDEC-','-DECIMAL_PLACES-']:
                self.window[k].update(disabled=True)
        if selected == 'Q':
            for k in ['-FIRST_PAREN-','-QFRAC-','-IRREDUCIBLE-','-QDEC-']:
                self.window[k].update(disabled=False)

    def _on_qrepr_changed(self, event):
        if event == '-QFRAC-':
            self.window['-IRREDUCIBLE-'].update(disabled=False)
            self.window['-DECIMAL_PLACES-'].update(disabled=True)
        if event == '-QDEC-':
            self.window['-IRREDUCIBLE-'].update(disabled=True)
            self.window['-DECIMAL_PLACES-'].update(disabled=False)

    def _on_nterms_changed(self, values):
        try:
            n = int(values['-NTERMS-'])
            self.window['-NTERMS_DISP-'].update('×'.join(['R'] * n) + ' -> R' if n >= 2 else '')
        except ValueError:
            self.window['-NTERMS_DISP-'].update('')

    def _on_toggle_input(self, checkbox_key, is_checked):
        for key in self.link_map[checkbox_key]:
            self.window[key].update(visible=is_checked)

    def _on_show_answer_toggle(self, values):
        show_answer = values.get('-SHOW_ANSWER-', False)
        disabled = not show_answer
        self.window['-ANS_NEW_PAGE-'].update(disabled=disabled)
        self.window['-ANS_FOOTER-'].update(disabled=disabled)

    def _on_footer_opt_toggle(self, values):
        ans_footer = values.get('-ANS_FOOTER-', False)
        disabled = not ans_footer
        self.window['-FOOTER_ROTATE-'].update(disabled=disabled)

    # ---------- Render Helpers ----------
    def _render_all_views(self, latex_only=False):
        builder = BlockBuilder(self.problems, self.settings)
        latex_renderer = LaTeXRenderer(builder, self.settings)
        latex_source = latex_renderer.render_source()
        self.window['-LATEX_VIEW-'].update(latex_source, disabled=False)
        self.window['-LATEX_VIEW-'].Widget.yview_moveto(0)

        if not latex_only:
            text_renderer = TextRenderer(builder)
            text_str = text_renderer.render()
            self.window['-TEXT_VIEW-'].update(text_str, disabled=False)
            self.window['-TEXT_VIEW-'].Widget.yview_moveto(0)

    # ---------- Validators / Utils ----------
    def not_empty(self, v): return bool(v.strip())
    def is_integer(self, v): return bool(re.fullmatch(r'\d+', v.strip()))
    def is_valid_date(self, v):
        if not re.fullmatch(r'\d{4}/\d{2}/\d{2}', v.strip()): return False
        try:
            datetime.strptime(v.strip(), '%Y/%m/%d'); return True
        except ValueError:
            return False
    def at_least_one_selected(self, values, keys):
        return any(values[k] for k in keys)
    def validate_num_problems(self, values):
        try:
            num_problems = int(values['-NPROBLEMS-'])
            n_terms = int(values['-NTERMS-'])
            domain = next(label for label in ['N','Z','Q'] if values.get(f'-DOMAIN_{label}-'))
            min_val = int(values['-MIN-']); max_val = int(values['-MAX-'])
            selected_ops = [v for op, v in self.arith_ops_dict.items() if values[op]]
            allow_zero = bool(values['-ALLOW_ZERO-'])
            if n_terms == 2 and domain == 'N':
                return num_problems <= max_2terms(min_val, max_val, selected_ops, domain, allow_zero)
            return True
        except Exception:
            return False
    def log(self, message, error=False):
        color = 'red' if error else 'white'
        prefix = '[ERROR]' if error else '[INFO]'
        self.window['-LOG-'].update(f"{prefix} {message}\n", append=True, text_color_for_value=color)
