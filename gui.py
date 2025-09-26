import re
import FreeSimpleGUI as sg
import json
import os
import copy
from datetime import datetime
from collections import Counter
from itertools import zip_longest
from settings import load_settings, save_settings, MAX_TERMS, MAX_POLYS
from generators.factory import generate_problem
from problems.factory import make_problem
from problems.parser import parse_latex_expr, parse_text_expr, extract_tag_from_tex
from renderer.latex_renderer import LaTeXRenderer
from renderer.text_renderer import TextRenderer
from export.latex2pdf import LaTeX2PDF
from utils.utils import max_2terms, dict_diff


class SettingsManager:
    """settings の適用・収集・検証を担当（GUIから分離）"""
    def __init__(self, settings, window):
        self.settings = settings
        self.window = window
        self.validation_rules = {}

    # --- 適用 ---
    def apply_to_gui(self):
        s = self.settings

        # ヘッダ設定の有効/無効
        if s['use_title']:
            self.window['-TITLE-'].update(disabled=False)
        if s['use_date']:
            self.window['-DATE-'].update(disabled=False)
        if s['use_name']:
            self.window['-NAME-'].update(disabled=False)
        # ドメイン別の有効/無効
        domain = s['domain_arith']
        if domain == 'Z':
            self.window['-FIRST_PAREN-'].update(disabled=False)
        elif domain == 'Q':
            self.window['-FIRST_PAREN-'].update(disabled=False)
            for k in ['-QFRAC-','-IRREDUCIBLE-','-QDEC-','-DECIMAL_PLACES-']:
                self.window[k].update(disabled=False)
        # seedの有効/無効
        if s['use_seed']:
            self.window['-SEED-'].update(disabled=False)
            self.window['-SEED_TODAY-'].update(disabled=False)
        # =の改行の有効/無効
        if s['show_equal']:
            self.window['-LINE_BREAK-'].update(disabled=False)
        # 解答表示の有効/無効
        if s['show_answer']:
            self.window['-ANS_NEWPAGE-'].update(disabled=False)
            self.window['-ANS_FOOTER-'].update(disabled=False)
            if s['ans_newpage']:
                self.window['-BOXED-'].update(disabled=False)
            if s['ans_footer']:
                self.window['-FOOTER_ROTATE-'].update(disabled=False)
        # タブ
        if s['prob_type'] == 'arithmetic':
            self.window['-TAB_ARITH-'].select()
        elif s['prob_type'] == 'expand':
            self.window['-TAB_EXPAND-'].select()
        # --- 四則演算 ---
        # 項数の表示
        n = int(s['n_terms'])
        self.window['-NTERMS_DISP-'].update('×'.join(['R'] * n) + ' -> R' if n >= 2 else '')
        # 乱数の有効/無効
        if s['use_custom']:
            self.window['-MIN-'].update(disabled=True)
            self.window['-MAX-'].update(disabled=True)

    def apply_settings_to_gui(self):
        s = self.settings
        self.window['-DIR_NAME-'].update(s['dir_name'])
        self.window['-FILE_NAME-'].update(s['file_name'])
        self.window['-PAPER-'].update(s['paper_size'])
        self.window['-FONTSIZE-'].update(s['font_size'])
        self.window['-MTOP-'].update(s['margin_top'])
        self.window['-MBOTTOM-'].update(s['margin_bottom'])
        self.window['-MLEFT-'].update(s['margin_left'])
        self.window['-MRIGHT-'].update(s['margin_right'])
        self.window['-CHK_LANDSCAPE-'].update(s['landscape'])
        self.window['-USE_TITLE-'].update(s['use_title'])
        self.window['-TITLE-'].update(s['title'])
        self.window['-USE_DATE-'].update(s['use_date'])
        self.window['-DATE-'].update(s['date'])
        self.window['-USE_NAME-'].update(s['use_name'])
        self.window['-NAME-'].update(s['name'])
        # --- 共通 ---
        self.window['-NPROBLEMS-'].update(s['num_problems'])
        self.window['-NCOLS-'].update(s['cols'])
        self.window['-ALLOW_ZERO-'].update(s['allow_zero'])
        self.window['-ALLOW_DUP-'].update(s['allow_dup'])
        self.window['-SHOW_EQUAL-'].update(s['show_equal'])
        self.window['-LINE_BREAK-'].update(s['line_break'])
        self.window['-SHOW_ANSWER-'].update(s['show_answer'])
        self.window['-ANS_NEWPAGE-'].update(s['answer_pos'])
        self.window['-BOXED-'].update(s['boxed'])
        self.window['-ANS_NEWPAGE-'].update(s['ans_newpage'])
        self.window['-ANS_FOOTER-'].update(s['ans_footer'])
        self.window['-FOOTER_ROTATE-'].update(s['footer_rotate'])
        self.window['-USE_SEED-'].update(s['use_seed'])
        self.window['-SEED-'].update(s['seed'])
        self.window['-TAB_GROUP-'].update(s['prob_type'])
        # --- 四則演算 ---
        self.window['-NTERMS-'].update(s['n_terms'])
        self.window['-ADD-'].update(s['ops']['+'])
        self.window['-SUB-'].update(s['ops']['-'])
        self.window['-MUL-'].update(s['ops']['*'])
        self.window['-DIV-'].update(s['ops']['/'])
        self.window['-FIRST_PAREN-'].update(s['first_paren'])
        self.window['-QFRAC-'].update(s['q_repr'])
        self.window['-IRREDUCIBLE-'].update(s['irreducible'])
        self.window['-DECIMAL_PLACES-'].update(s['decimal_places'])
        self.window['-MIN-'].update(s['min_val'])
        self.window['-MAX-'].update(s['max_val'])
        # if not s['use_custom']:
        #     s['custom_ranges'] = [(int(self.window[f'-MIN-']), int(self.window[f'-MAX-'])) for _ in range(int(MAX_TERMS))]
        # --- 展開 ---
        self.window['-NPOLYS-'].update(s['n_polys'])
        self.window['-MONIC_EXP-'].update(s['monic'])
        self.window['-MAX_TERMS_EXP-'].update(s['max_terms'])
        self.window['-MIN_TERMS_EXP-'].update(s['min_terms'])
        self.window['-VAR_TYPE_EXP-'].update(s['var_type'])
        self.window['-VAR_SET_EXP-'].update(s['var_set'])
        for label in ['N','Z','Q']:
            if label == s['domain_arith']:
                self.window[f'-DOMAIN_ARITH_{label}-'].update(True)
        for label in ['Z','Q']:
            if label == s['domain_exp']:
                self.window[f'-DOMAIN_EXP_{label}-'].update(True)
        self.window['-FIRST_MINUS_EXP-'].update(s['first_minus'])

    # --- 収集 ---
    def collect_from_values(self, values):
        prob_type = {
            '-TAB_ARITH-': 'arithmetic',
            '-TAB_EXPAND-': 'expand',
        }
        s = self.settings
        s['dir_name'] = values['-DIR_NAME-']
        s['file_name'] = values['-FILE_NAME-']
        s['paper_size'] = values['-PAPER-']
        s['font_size'] = values['-FONTSIZE-']
        s['margin_top'] = int(values['-MTOP-'])
        s['margin_bottom'] = int(values['-MBOTTOM-'])
        s['margin_left'] = int(values['-MLEFT-'])
        s['margin_right'] = int(values['-MRIGHT-'])
        s['landscape'] = values['-CHK_LANDSCAPE-']
        s['use_title'] = values['-USE_TITLE-']
        s['title'] = values['-TITLE-']
        s['use_date'] = values['-USE_DATE-']
        s['date'] = values['-DATE-']
        s['use_name'] = values['-USE_NAME-']
        s['name'] = values['-NAME-']
        # --- 共通 ---
        s['num_problems'] = int(values['-NPROBLEMS-'])
        s['cols'] = int(values['-NCOLS-'])
        s['allow_zero'] = values['-ALLOW_ZERO-']
        s['allow_dup'] = values['-ALLOW_DUP-']
        s['show_equal'] = values['-SHOW_EQUAL-']
        s['line_break'] = values['-LINE_BREAK-']
        s['show_answer'] = values['-SHOW_ANSWER-']
        s['answer_pos'] = 'new_page' if values['-ANS_NEWPAGE-'] else 'footer'
        s['boxed'] = values['-BOXED-']
        s['ans_newpage'] = values['-ANS_NEWPAGE-']
        s['ans_footer'] = values['-ANS_FOOTER-']
        s['footer_rotate'] = values['-FOOTER_ROTATE-']
        s['use_seed'] = values['-USE_SEED-']
        s['seed'] = values['-SEED-']
        s['prob_type'] = prob_type[values['-TAB_GROUP-']]
        # --- 四則演算 ---
        s['n_terms'] = int(values.get('-NTERMS-', 2))
        s['ops'] = { '+': values['-ADD-'], '-': values['-SUB-'], '*': values['-MUL-'], '/': values['-DIV-'] }
        s['first_paren'] = values['-FIRST_PAREN-']
        s['q_repr'] = 'frac' if values['-QFRAC-'] else 'decimal'
        s['irreducible'] = values['-IRREDUCIBLE-'] if values['-TAB_GROUP-'] == 'arithmetic' else True
        s['decimal_places'] = values['-DECIMAL_PLACES-']
        s['min_val'] = values['-MIN-']
        s['max_val'] = values['-MAX-']
        if not s['use_custom']:
            s['custom_ranges'] = [(int(values[f'-MIN-']), int(values[f'-MAX-'])) for _ in range(int(MAX_TERMS))]
        # --- 展開 ---
        s['n_polys'] = int(values.get('-NPOLYS-', 2))
        s['monic'] = values['-MONIC_EXP-']
        s['max_terms'] = values['-MAX_TERMS_EXP-']
        s['min_terms'] = values['-MIN_TERMS_EXP-']
        s['var_type'] = values['-VAR_TYPE_EXP-']
        s['var_set'] = values['-VAR_SET_EXP-']
        s['domain_arith'] = next(label for label in ['N','Z','Q'] if values.get(f'-DOMAIN_ARITH_{label}-'))
        s['domain_exp'] = next(label for label in ['Z','Q'] if values.get(f'-DOMAIN_EXP_{label}-'))
        s['first_minus'] = values['-FIRST_MINUS_EXP-']
        return s

    def update_from_values(self, values):
        s = {}
        s['dir_name'] = values['-DIR_NAME-']
        s['file_name'] = values['-FILE_NAME-']
        s['paper_size'] = values['-PAPER-']
        s['font_size'] = values['-FONTSIZE-']
        s['margin_top'] = int(values['-MTOP-'])
        s['margin_bottom'] = int(values['-MBOTTOM-'])
        s['margin_left'] = int(values['-MLEFT-'])
        s['margin_right'] = int(values['-MRIGHT-'])
        s['landscape'] = values['-CHK_LANDSCAPE-']
        s['use_title'] = values['-USE_TITLE-']
        s['title'] = values['-TITLE-']
        s['use_date'] = values['-USE_DATE-']
        s['date'] = values['-DATE-']
        s['use_name'] = values['-USE_NAME-']
        s['name'] = values['-NAME-']
        s['cols'] = int(values['-NCOLS-'])
        s['show_equal'] = values['-SHOW_EQUAL-']
        s['line_break'] = values['-LINE_BREAK-']
        s['first_paren'] = values['-FIRST_PAREN-']
        s['show_answer'] = values['-SHOW_ANSWER-']
        s['answer_pos'] = 'new_page' if values['-ANS_NEWPAGE-'] else 'footer'
        s['boxed'] = values['-BOXED-']
        s['ans_newpage'] = values['-ANS_NEWPAGE-']
        s['ans_footer'] = values['-ANS_FOOTER-']
        s['footer_rotate'] = values['-FOOTER_ROTATE-']
        s = self.settings | s
        diff = dict_diff(s, self.settings)
        return s, diff

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
            '-USE_TITLE-': ['-TITLE-'],
            '-USE_DATE-': ['-DATE-', '-BTN_DATE-'],
            '-USE_NAME-': ['-NAME-'],
            '-USE_SEED-': ['-SEED-', '-SEED_TODAY-'],
            '-SHOW_EQUAL-': ['-LINE_BREAK-'],
        }

    def build_main(self):
        s = self.settings

        # ----- ドキュメント設定 -----
        doc_frame = sg.Frame('ドキュメント設定', [
            [
                sg.Text('出力フォルダ:'), sg.InputText(default_text=s['dir_name'], key='-DIR_NAME-', size=(30, 1)),
                sg.Button('選択', target='-DIR_NAME-', key='-SELECT_DIR-', pad=(0, 0))
            ],[
                sg.Text('ファイル名:'), sg.InputText(default_text=s['file_name'], key='-FILE_NAME-', size=(30, 1))
            ],[
                sg.Text('用紙サイズ:'), sg.Combo(['A3','A4','A5','B4','B5'], default_value=s['paper_size'], key='-PAPER-'),
                sg.Checkbox('横向き', key='-CHK_LANDSCAPE-', default=s['landscape']),
                sg.Text('基準フォントサイズ:'), sg.Combo(['10pt','11pt','12pt'], key='-FONTSIZE-', default_value=s['font_size'])
            ],[
                sg.Text('余白(mm): 上'), sg.InputText(str(s['margin_top']), size=(4, 1), key='-MTOP-'),
                sg.Text('下'), sg.InputText(str(s['margin_bottom']), size=(4, 1), key='-MBOTTOM-'),
                sg.Text('左'), sg.InputText(str(s['margin_left']), size=(4, 1), key='-MLEFT-'),
                sg.Text('右'), sg.InputText(str(s['margin_right']), size=(4, 1), key='-MRIGHT-')
            ]
        ], expand_x=True)

        # ----- ヘッダ設定 -----
        header_frame = sg.Frame('ヘッダ設定', [
            [
                sg.Checkbox('表題', key='-USE_TITLE-', default=s['use_title'], enable_events=True),
                sg.InputText(default_text=s['title'], key='-TITLE-', disabled=True)
            ],[
                sg.Checkbox('日付', key='-USE_DATE-', default=s['use_date'], enable_events=True),
                sg.InputText(default_text=s['date'], key='-DATE-', size=(12, 1), disabled=True),
                sg.CalendarButton('選択', target='-DATE-', format='%Y/%m/%d', disabled=True, key='-BTN_DATE-', size=(5, 1), pad=(0, 0))
            ],[
                sg.Checkbox('氏名', key='-USE_NAME-', default=s['use_name'], enable_events=True),
                sg.InputText(default_text=s['name'], key='-NAME-', disabled=True)
            ]
        ], expand_x=True)

        # ----- 本文設定 -----
        common = sg.Column([
            [
                sg.Text('問題数:'), sg.InputText(default_text=str(s['num_problems']), size=(5, 1), key='-NPROBLEMS-'),
                sg.Text('列数:'), sg.InputText(default_text=str(s['cols']), size=(5, 1), key='-NCOLS-')
            ],[
                sg.Checkbox('Seed値:', key='-USE_SEED-', default=s['use_seed'], enable_events=True),
                sg.InputText(default_text=s['seed'], key='-SEED-', disabled=True, size=(15, 1)),
                sg.Button('今日の日付', key='-SEED_TODAY-', disabled=True)
            ],[
                sg.Checkbox('乱数に0を許容', key='-ALLOW_ZERO-', default=s['allow_zero'])
            ],[
                sg.Checkbox('問題の重複許可', key='-ALLOW_DUP-', default=s['allow_dup'])
            ],[
                sg.Checkbox('= を表示', key='-SHOW_EQUAL-', default=s['show_equal'], enable_events=True),
                sg.Checkbox('改行', key='-LINE_BREAK-', default=s['line_break'], disabled=True)
            ],[
                sg.Checkbox("解答表示", key="-SHOW_ANSWER-", default=s['show_answer'], enable_events=True),
                sg.Text("場所:"),
                sg.Radio("新規ページ", "ANSWER_POS", key="-ANS_NEWPAGE-", default=s['ans_newpage'], enable_events=True, disabled=True),
                sg.Checkbox('囲み枠', key='-BOXED-', default=s['boxed'], disabled=True),
                sg.Radio("フッタ", "ANSWER_POS", key="-ANS_FOOTER-", default=s['ans_footer'], enable_events=True, disabled=True),
                sg.Checkbox('回転', key='-FOOTER_ROTATE-', default=s['footer_rotate'], disabled=True)
            ],[
                sg.Text('乱数 min:'), sg.InputText(default_text=s['min_val'], size=(5, 1), key='-MIN-'),
                sg.Text('max:'), sg.InputText(default_text=s['max_val'], size=(5, 1), key='-MAX-'),
                sg.Text('カスタム有効', key='-CUSTOM_DISP-', text_color='blue', visible=False)
            ]
        ])

        self.domain_options = ['N', 'Z', 'Q', 'R', 'C']

        # --- 四則演算 ---
        self.ops_dict = {
            '+': '+算',
            '-': '−算',
            '*': '×算',
            '/': '÷算'
        }
        self.arith_ops_dict = {
            '-ADD-': '+',
            '-SUB-': '-',
            '-MUL-': '*',
            '-DIV-': '/'
        }

        # 項数ラベル
        terms_row = [
            sg.Text('項数:'),
            sg.Spin([2, 3, 4], initial_value=s['n_terms'], key='-NTERMS-', enable_events=True),
            sg.Text('R×R -> R', key='-NTERMS_DISP-', text_color='blue')
        ]

        arith_ops_row = [sg.Text('演算:')]
        for k, op in self.arith_ops_dict.items():
            arith_ops_row.append(sg.Checkbox(self.ops_dict[op], key=k, default=s['ops'][op]))

        arith_domain_row = [sg.Text('領域:')]
        for label in self.domain_options[:3]:
            arith_domain_row.append(sg.Radio(label, 'DOMAIN_ARITH', key=f'-DOMAIN_ARITH_{label}-', default=(label==s['domain_arith']), enable_events=True))
        
        # オプション
        arith_domain_options = sg.Frame('領域オプション', [
            [
                sg.Checkbox('先頭の括弧', key='-FIRST_PAREN-', default=s['first_paren'], disabled=True)
            ],[
                sg.Radio('分数', 'QREP', key='-QFRAC-', default=s['frac'], enable_events=True, disabled=True),
                sg.Checkbox('既約', key='-IRREDUCIBLE-', default=s['irreducible'], disabled=True),
                sg.Radio('小数', 'QREP', key='-QDEC-', default=s['decimal'], enable_events=True, disabled=True),
                sg.Text('小数点以下:'), sg.Spin([i for i in range(1, 6)], initial_value=s['decimal_places'], key='-DECIMAL_PLACES-', disabled=True)
            ]
          ], pad=(30,0), expand_x=True, size=(400, 80)
        )

        # タブ1: 四則演算
        tab_arith = sg.Column([
                terms_row,
                arith_ops_row,
                arith_domain_row,
                [arith_domain_options], # ここで横幅を調整
                [
                    sg.Button('カスタム', key='-CUSTOM-')
                ]
            ], scrollable=True, vertical_scroll_only=True, expand_y=True
        )

        # --- 展開 ---

        exp_domain_row = [sg.Text('領域:')]
        for label in self.domain_options[1:3]:
            exp_domain_row.append(sg.Radio(label, 'DOMAIN_EXP', key=f'-DOMAIN_EXP_{label}-', default=(label==s['domain_exp']), enable_events=True))

        # タブ2: 展開
        tab_expand = sg.Column([
                [
                    sg.Text('多項式数:'), sg.Spin([2, 3, 4], initial_value=s['n_polys'], key='-NPOLYS-', enable_events=True),
                    sg.Text('R[x]×R[x] -> R[x]', key='-NPOLYS_DISP-', text_color='blue')
                ],[
                    sg.Text('文字タイプ:'),
                    sg.Combo(['[x]', '[x,y]', '[x,y,z]'], default_value=s['var_type'], key='-VAR_TYPE_EXP-', readonly=True, enable_events=True),
                    sg.Text('1元n次', key='-VAR_TYPE_DISP-', text_color='blue')
                ],[
                    sg.Text('文字セット:'),
                    sg.Combo(['x,y,z,...', 'a,b,c,...'], default_value=s['var_set'], key='-VAR_SET_EXP-', readonly=True)
                ],[
                    sg.Checkbox('最高次係数1', default=s['monic'], key='-MONIC_EXP-')
                ],[
                    sg.Checkbox('最高次係数の負数を許可', default=s['first_minus'], key='-FIRST_MINUS_EXP-')
                ],[
                    sg.Text('最大次数(項数):'),
                    sg.Spin([1, 2, 3, 4], initial_value=s['max_terms'], key='-MAX_TERMS_EXP-', enable_events=True),
                    sg.Text('最小次数(項数):'),
                    sg.Spin([1, 2, 3, 4], initial_value=s['min_terms'], key='-MIN_TERMS_EXP-', enable_events=True)
                ],
                exp_domain_row
            ], scrollable=True, vertical_scroll_only=True, expand_y=True
        )

        tab_group = sg.TabGroup([
            [
                sg.Tab('四則演算', [[tab_arith]], key='-TAB_ARITH-'),
                sg.Tab('展開', [[tab_expand]], key='-TAB_EXPAND-')
            ]
        ], key='-TAB_GROUP-', expand_x=True, expand_y=True)

        execution_buttons = [
            sg.Button('LaTeX生成', key='-GEN_LATEX-'),
            sg.Button('LaTeX読込', key='-LOAD_LATEX-'),
            sg.Button('LaTeX更新', key='-UPDATE_LATEX-', disabled=True),
            sg.Button('PDF生成', key='-GEN_PDF-'),
            sg.Button('終了')
        ]

        body_frame = sg.Frame('本文設定', [
            [common],
            [tab_group]
        ], expand_x=True, expand_y=True)

        left_col = sg.Column([
            [sg.Button('設定読込', key='-LOAD_SETTINGS-'), sg.Button('設定保存', key='-SAVE_SETTINGS-')],
            [doc_frame],
            [header_frame],
            [body_frame]
        ], vertical_alignment='top', scrollable=False, expand_x=True, expand_y=True)

        right_col = sg.Column([
            [
                sg.TabGroup([
                    [
                        sg.Tab('LaTeXビュー', [
                            [sg.Multiline('', size=(60, 35), key='-LATEX_VIEW-', autoscroll=True, disabled=True)]
                        ])
                    ],[
                        sg.Tab('Textビュー', [
                            [sg.Multiline('', size=(60, 35), key='-TEXT_VIEW-', autoscroll=True, disabled=True, enable_events=True)]
                        ])
                    ]
                ], key='-TAB_VIEW-', expand_x=True, expand_y=True)
            ],[
                sg.Multiline('', key='-LOG-', size=(60, 8),
                    text_color='white', background_color='black',
                    autoscroll=True, disabled=True)
            ],
            execution_buttons,
        ], vertical_alignment='top', expand_y=True)

        layout = [[left_col, right_col]]

        return layout

    def build_custom(self, settings):
        s = settings
        custom_ranges = s.get('custom_ranges', [('', '') for _ in range(MAX_TERMS)])
        disabled = [(i >= s['n_terms']) or not s['use_custom'] for i in range(MAX_TERMS)]
        layout = [
            [sg.Frame('乱数オプション', [
                [sg.Checkbox('カスタム乱数', key='-USE_CUSTOM-', default=s['use_custom'], enable_events=True)],
                *[[sg.Text(f'項{i+1}: min'), 
                   sg.InputText(str(custom_ranges[i][0]), size=(5,1), key=f'-MIN{i}-', disabled=disabled[i]),
                   sg.Text('max'),
                   sg.InputText(str(custom_ranges[i][1]), size=(5,1), key=f'-MAX{i}-', disabled=disabled[i])]
                  for i in range(MAX_TERMS)]
              ])
            ],
            [sg.Button('閉じる')]
        ]

        return layout

    def ask_problem_type(self):
        """問題TYPEを聞く"""
        layout = [
            [sg.Text("問題のタイプを判定できませんでした。選択してください:")],
            [sg.Combo(['arithmetic', 'expand'], default_value='arithmetic', key='-TYPE-')],
            [sg.Button('OK'), sg.Button('Cancel')]
        ]

        window = sg.Window('問題タイプ選択', layout, modal=True)

        while True:
            event, values = window.read()
            if event in (sg.WINDOW_CLOSED, 'Cancel'):
                window.close()
                return None
            elif event == 'OK':
                choice = values['-TYPE-']
                window.close()
                return choice.lower() if choice else None

class MyApp:
    def __init__(self):
        self.settings = load_settings()
        self.settings_origin = copy.deepcopy(self.settings)
        if self.settings.get('use_date', False) and not self.settings.get('date'):
            self.settings['date'] = datetime.today().strftime('%Y/%m/%d')

        # 四則演算マップ（これだけMyAppで管理）
        self.ops_dict = {'+': '+算', '-': '−算', '*': '×算', '/': '÷算'}
        self.arith_ops_dict = {'-ADD-': '+', '-SUB-': '-', '-MUL-': '*', '-DIV-': '/'}
        self.domain_arith_options = ['N', 'Z', 'Q']
        self.domain_exp_options = ['Z', 'Q']

        # --- View ---
        self.view = ViewBuilder(self.settings)
        last_loc = self.settings.get('window_location', (5, 5))
        self.window = sg.Window(
            'LaTeX de Arithmetics',
            self._build_layout(),
            location=last_loc,
            finalize=True
        )
        self.custom_window = None # カスタムウィンドウの存在
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
        return self.view.build_main()

    def _link_map(self):
        return {
            '-USE_TITLE-': ['-TITLE-'],
            '-USE_DATE-': ['-DATE-', '-BTN_DATE-'],
            '-USE_NAME-': ['-NAME-'],
            '-USE_SEED-': ['-SEED-', '-SEED_TODAY-'],
            '-SHOW_EQUAL-': ['-LINE_BREAK-'],
        }

    # ---------- Validation ----------
    def _bind_validation_rules(self):
        # ★ここで「辞書キー重複」を解消して一箇所に集約
        # 既存の not_empty / is_integer / is_valid_date / at_least_one_selected / validate_num_problems を使う
        rules = {
            '-TITLE-': [
              (lambda v: (not self.window['-USE_TITLE-'].get()) or len(v) > 0, "表題を入力してください")
            ],
            '-DATE-': [
              (lambda v: (not self.window['-USE_DATE-'].get()) or self.not_empty(v), "日付を入力してください"),
              (lambda v: (not self.window['-USE_DATE-'].get()) or self.is_valid_date(v), '日付はYYYY/MM/DD形式で正しく入力してください')
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
            '-SELECT_DIR-': self._on_dir_clicked,
            '-CUSTOM-': self._on_custom_clicked,
            '-SEED_TODAY-': self._on_today_clicked,
            '-LOAD_SETTINGS-': self._on_load_settings_clicked,
            '-SAVE_SETTINGS-': self._on_save_settings_clicked,
        }
        while True:
            window, event, values = sg.read_all_windows(timeout=100) # timeoutでポーリング
            if window == self.window:
                if event in (sg.WINDOW_CLOSED, '終了'):
                    # 閉じる直前に位置を保存
                    loc = self.window.current_location()
                    if loc == (None, None):
                        loc = self.settings.get('window_location', (10, 25))
                    self.settings_origin['window_location'] = loc
                    save_settings(self.settings_origin)
                    break

                # 共通：チェックボックス可視切替
                if event in self.link_map:
                    self._on_toggle_input(event, values)

                if event == '-SHOW_ANSWER-':
                    self._on_show_answer_toggle(values)
                if event in [f'-ANS_{label}-' for label in ['NEWPAGE', 'FOOTER']]:
                    self._on_newpage_opt_toggle(values)
                    self._on_footer_opt_toggle(values)

                # 入力系イベント
                if event == '-NTERMS-':
                    self._on_nterms_changed(values)
                if event in [f'-DOMAIN_ARITH_{label}-' for label in self.domain_arith_options]:
                    self._on_domain_changed(values)
                # if event in [f'-DOMAIN_EXP_{label}-' for label in self.domain_exp_options]:
                #     self._on_domain_changed(values)
                if event in ['-QFRAC-', '-QDEC-']:
                    self._on_qrepr_changed(event)

                if event == '-NPOLYS-':
                    self._on_npolys_changed(values)
                if event == '-VAR_TYPE_EXP-':
                    self._on_var_type_chenged(values)

                if event == '-MAX_TERMS_EXP-':
                    max_val = int(values['-MAX_TERMS_EXP-'])
                    min_val = int(values['-MIN_TERMS_EXP-'])
                    if min_val > max_val:
                        self.window['-MIN_TERMS_EXP-'].update(max_val)

                elif event == '-MIN_TERMS_EXP-':
                    max_val = int(values['-MAX_TERMS_EXP-'])
                    min_val = int(values['-MIN_TERMS_EXP-'])
                    if min_val > max_val:
                        self.window['-MAX_TERMS_EXP-'].update(min_val)

                # Textビューの編集検知
                if event == '-TEXT_VIEW-':
                    self._on_text_changed()

                # ボタン類
                if event in handler:
                    handler[event](values)

            elif window == self.custom_window:
                if event in (sg.WINDOW_CLOSED, '閉じる'):
                    if self.settings['use_custom']:
                        self.settings['custom_ranges'] = [(int(values[f'-MIN{i}-']), int(values[f'-MAX{i}-'])) for i in range(int(MAX_TERMS))]
                    self.custom_window.close()
                    self.custom_window = None

                if event == '-USE_CUSTOM-':
                    self._on_custom_changed(values)

        self.window.close()

    # ---------- Handlers ----------
    def _on_save_settings_clicked(self, values):
        """ユーザーにファイル名を入力させて保存"""
        filename = sg.popup_get_text("保存する設定ファイル名を入力してください", default_text="user_settings.json")
        if filename:
            if not filename.endswith(".json"):
                filename += ".json"
            save_settings(self.settings, filename)
            self.log(f'{filename} 保存完了')


    def _on_load_settings_clicked(self, values):
        """ユーザーにファイルを選ばせてロード"""
        filename = sg.popup_get_file("設定ファイルを選択してください", file_types=(("JSON Files", "*.json"),))
        if filename:
            self.settings = load_settings(filename)
            self.settings_origin = copy.deepcopy(self.settings)
            self.settings_mgr.settings = self.settings
            self.settings_mgr.apply_settings_to_gui()
            self.settings_mgr.apply_to_gui()
            self.log(f'{filename} 読込完了')

    def _on_dir_clicked(self, values):
        """
        ユーザーに出力ディレクトリを選ばせる
        default_path: 最初に表示するフォルダ
        戻り値: 選択したパス、キャンセルなら None
        """
        current_dir = os.getcwd()
        folder = sg.popup_get_folder(
            "PDFの出力先フォルダを選択してください",
            default_path=current_dir or os.path.expanduser("~"),
            no_window=True
        )
        if folder and os.path.isdir(folder):
            if '~' in folder:
                folder = os.path.relpath(folder, start=current_dir) # 相対パス
            self.window['-DIR_NAME-'].update(folder)
        return None

    def _on_custom_clicked(self, values):
        """カスタム設定ウィンドウを表示"""
        if self.custom_window is not None:
            # すでに開いている場合はフォーカスを戻す
            self.custom_window.bring_to_front()
            return
        layout = self.view.build_custom(self.settings)
        self.custom_window = sg.Window('カスタム設定', layout, modal=False, finalize=True)

    def _on_today_clicked(self, values):
        """seed値を今日の日付から生成"""
        self.window['-SEED-'].update(datetime.today().strftime('%Y%m%d'))

    def _on_generate_clicked(self, values):
        errs = self.settings_mgr.validate(values)
        if errs: return self.log('\n'.join(errs), error=True)

        self.settings_mgr.collect_from_values(values)
        # Problem作成
        self.problems = [make_problem(data, self.settings) for data in generate_problem(self.settings)]
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

        edited = self.sync.cleaned_lines(converted_text)
        current = [p.to_text() for p in self.problems]
        diff, dup = self.sync.diff_and_dup(current, edited)
        if not diff and (self.settings.get('allow_dup', True) or not dup):
            return
        msg = '変更確認\n' + '\n'.join(diff)
        if not self.settings['allow_dup'] and dup:
            msg += '\n※重複あり\n' + '\n'.join(dup)
        if sg.popup_ok_cancel(msg, keep_on_top=True) != 'OK':
            return

        new_problems = []
        prob_type = self.settings['prob_type']
        var_type = self.settings['var_type']
        var_set = self.settings['var_set']
        for i, expr_text in enumerate(edited):
            if prob_type == 'arithmetic':
                data = parse_text_expr(expr_text, 'arithmetic')
            elif prob_type == 'expand':
                data = parse_text_expr(expr_text, 'expand', var_type, var_set)
            if i < len(self.problems):
                problem = self.problems[i].from_values(data, self.settings)
            else:
                problem = make_problem(data, self.settings)
            new_problems.append(problem)
        self.problems = new_problems

        diff_settings = self._update_settings(_values)
        if diff_settings:
            self._render_all_views()
        else:
            self._render_all_views(latex_only=True)
        self.window['-UPDATE_LATEX-'].update(disabled=True)
        self.window['-GEN_PDF-'].update(disabled=False)
        self.log('LaTeX更新完了')

    def _on_load_latex_clicked(self, _values):
        filename = sg.popup_get_file("TeXファイルを選択してください")
        if not filename: return
        with open(filename, encoding="utf-8") as f:
            tex_content = f.read()

        problem_strs = self.sync.extract_items_from_tex(tex_content)
        seed = extract_tag_from_tex(tex_content, "SEED")
        prob_type = extract_tag_from_tex(tex_content, "TYPE")
        if prob_type == 'expand':
            var_type = extract_tag_from_tex(tex_content, "VAR_TYPE")
            var_set = extract_tag_from_tex(tex_content, "VAR_SET")
        if seed is not None:
            self.window['-USE_SEED-'].update(True)
            self.window['-SEED-'].update(seed, disabled=False)
        if prob_type is None:
            probl_type = self.view.ask_problem_type()
        new_problems = []
        for i, expr_latex in enumerate(problem_strs):
            if prob_type == 'arithmetic':
                data = parse_latex_expr(expr_latex, 'arithmetic')
            elif prob_type == 'expand':
                data = parse_latex_expr(expr_latex, 'expand', var_type=var_type, var_set=var_set)
            problem = make_problem(data, self.settings)
            new_problems.append(problem)
        self.problems = new_problems
        
        self._render_all_views()
        self.log('LaTeX読込完了')

    def _on_generate_pdf_clicked(self, values):
        diff_settings = self._update_settings(values)
        filename = self.settings['file_name'].strip() or sg.popup_get_text('ファイル名を入力してください')
        if not filename: return
        if self.problems == []:
            self.problems = [make_problem(data, self.settings) for data in generate_problem(self.settings)]
        latex_renderer = LaTeXRenderer(self.problems, self.settings)
        latex_str = latex_renderer.render_latex()
        if diff_settings:
            self._render_all_views()
        pdf_gen = LaTeX2PDF.from_latex(latex_str, self.settings)
        pdf_path = pdf_gen.compile_pdf(filename)
        save_settings(self.settings)
        self.settings_origin = copy.deepcopy(self.settings)
        self.log(f'PDF生成完了: {pdf_path}')

    def _on_text_changed(self):
        current_text = self.window['-TEXT_VIEW-'].get()
        current_lines = self.sync.cleaned_lines(current_text)
        original_lines = [p.to_text() for p in self.problems]
        diff, dup = self.sync.diff_and_dup(original_lines, current_lines)

        # 差分状態が前回と変わったときだけUI更新
        if diff != self._text_changed_diff:
            self._text_changed_diff = diff
            if diff:
                self.window['-UPDATE_LATEX-'].update(disabled=False)
                self.window['-GEN_PDF-'].update(disabled=True)
            else:
                self.window['-UPDATE_LATEX-'].update(disabled=True)
                self.window['-GEN_PDF-'].update(disabled=False)

    def _on_domain_changed(self, values):
        selected = next((label for label in self.domain_arith_options if values.get(f'-DOMAIN_ARITH_{label}-')), 'N')
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
            self.settings['n_terms'] = n
            if self.custom_window:
                for i in range(MAX_TERMS):
                    disabled = (i >= n) or not self.settings['use_custom']
                    self.custom_window[f'-MIN{i}-'].update(disabled=disabled)
                    self.custom_window[f'-MAX{i}-'].update(disabled=disabled)
            self.window['-NTERMS_DISP-'].update('×'.join(['R'] * n) + ' -> R' if n >= 2 else '')
        except ValueError:
            self.window['-NTERMS_DISP-'].update('')

    def _on_npolys_changed(self, values):
        try:
            n = int(values['-NPOLYS-'])
            self.settings['n_polys'] = n
            if self.custom_window:
                for i in range(MAX_POLYS):
                    disabled = (i >= n)
            self.window['-NPOLYS_DISP-'].update('×'.join(['R[x]'] * n) + ' -> R[x]' if n >= 2 else '')
        except ValueError:
            self.window['-NPOLYS_DISP-'].update('')

    def _on_var_type_chenged(self, values):
        try:
            if values['-VAR_TYPE_EXP-'] == '[x]':
                self.window['-VAR_TYPE_DISP-'].update('1元n次')
            elif values['-VAR_TYPE_EXP-'] == '[x,y]':
                self.window['-VAR_TYPE_DISP-'].update('2元n次')
            elif values['-VAR_TYPE_EXP-'] == '[x,y,z]':
                self.window['-VAR_TYPE_DISP-'].update('n元1次')
        except ValueError:
            self.window['-VAR_TYPE_DISP-'].update('')
            

    def _on_toggle_input(self, key, values):
        if key not in self.link_map:
            return
        is_checked = values.get(key, False)
        for target in self.link_map[key]:
            self.window[target].update(disabled=not is_checked)

    def _on_show_answer_toggle(self, values):
        show_answer = values.get('-SHOW_ANSWER-', False)
        disabled = not show_answer
        self.window['-ANS_NEWPAGE-'].update(disabled=disabled)
        self.window['-ANS_FOOTER-'].update(disabled=disabled)
        if values['-ANS_NEWPAGE-']:
            self.window['-BOXED-'].update(disabled=disabled)
        if values['-ANS_FOOTER-']:
            self.window['-FOOTER_ROTATE-'].update(disabled=disabled)

    def _on_newpage_opt_toggle(self, values):
        ans_newpage = values.get('-ANS_NEWPAGE-', False)
        disabled = not ans_newpage
        self.window['-BOXED-'].update(disabled=disabled)

    def _on_footer_opt_toggle(self, values):
        ans_footer = values.get('-ANS_FOOTER-', False)
        disabled = not ans_footer
        self.window['-FOOTER_ROTATE-'].update(disabled=disabled)

    # ----- Custom Window -----
    def _on_custom_changed(self, values):
        use_custom = values['-USE_CUSTOM-']
        self.settings['use_custom'] = values['-USE_CUSTOM-']
        n_terms = int(self.settings['n_terms'])
        # 共通乱数入力はカスタムOFFのとき有効
        self.window['-MIN-'].update(disabled=use_custom)
        self.window['-MAX-'].update(disabled=use_custom)
        self.window['-CUSTOM_DISP-'].update(visible=use_custom)
        if self.custom_window is not None:
            for i in range(MAX_TERMS):
                disabled = (i >= n_terms) or not use_custom
                self.custom_window[f'-MIN{i}-'].update(disabled=disabled)
                self.custom_window[f'-MAX{i}-'].update(disabled=disabled)

    # ---------- Render Helpers ----------
    def _render_all_views(self, latex_only=False):
        latex_renderer = LaTeXRenderer(self.problems, self.settings)
        latex_source = latex_renderer.render_source()
        self.window['-LATEX_VIEW-'].update(latex_source, disabled=False)
        self.window['-LATEX_VIEW-'].Widget.yview_moveto(0)

        if not latex_only:
            text_renderer = TextRenderer(self.problems, self.settings)
            text_str = text_renderer.render()
            self.window['-TEXT_VIEW-'].update(text_str, disabled=False)
            self.window['-TEXT_VIEW-'].Widget.yview_moveto(0)

    def _update_settings(self, values):
        s, diff = self.settings_mgr.update_from_values(values)
        if diff:
            self.settings = s
            for prob in self.problems:
                prob.first_paren = self.settings['first_paren']
                prob.show_equal = self.settings['show_equal']
                prob.line_break = self.settings['line_break']
        return diff

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
            domain = next(label for label in ['N','Z','Q'] if values.get(f'-DOMAIN_ARITH_{label}-'))
            min_val = int(values['-MIN-']); max_val = int(values['-MAX-'])
            selected_ops = [v for op, v in self.arith_ops_dict.items() if values[op]]
            allow_zero = bool(values['-ALLOW_ZERO-'])
            if n_terms == 2 and domain in ['N', 'Z']:
                return num_problems <= max_2terms(min_val, max_val, selected_ops, domain, allow_zero)
            return True
        except Exception:
            print('hoge')
            return False
    def log(self, message, error=False):
        dt_now = datetime.now().strftime('%H:%M')
        color = 'red' if error else 'white'
        prefix = '[ERROR]' if error else '[INFO]'
        self.window['-LOG-'].update(f"{dt_now} {prefix} {message}\n", append=True, text_color_for_value=color)
    def apply_settings_to_gui(self, settings):
        self.window['--']
