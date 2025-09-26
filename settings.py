import os
import sys
import platform
import json
from datetime import datetime

MAX_TERMS = 4
MAX_POLYS = 4

# ------------------------------
# 用紙・レイアウト設定
# ------------------------------
DOC_SETTINGS = {
    'window_location': (10, 25), # 起動時のwindowの位置
    'file_name': 'output',       # ファイル名
    'dir_name': '~/Documents/LaTeXOutput', # 出力フォルダ
    'paper_size': 'A4',          # 'A3', 'A4', 'A5', 'B4', 'B5'
    'font_size': '11pt',         # '10pt', '11pt', '12pt'
    'margin_top': 25,            # 余白(mm)
    'margin_bottom': 35,
    'margin_left': 15,
    'margin_right': 15,
    'landscape': False,
    'use_title': False,
    'title': 'LaTeX de Arithmetics',                 # 表題
    'use_date': False,
    'date': '',                  # 日付 YYYY/MM/DD
    'use_name': False,
    'name': r'組\hspace{10mm}番\ 氏名(\hspace{50mm})', # 氏名
}

# ------------------------
# 共通問題設定
# ------------------------
COMMON_SETTINGS = {
    'num_problems': 48,          # 問題数
    'cols': 4,                   # 列数
    'allow_zero': False,         # 0を許容
    'allow_dup': False,          # 重複許可
    'show_equal': True,          # =表示
    'line_break': False,
    'min_val': -9,                # 値の最小
    'max_val': 9,                # 値の最大
    'show_answer': False,        # 解答表示
    'answer_pos': 'new_page',    # 表示場所
    'boxed': True,
    'ans_newpage': True,
    'ans_footer': False,
    'footer_rotate': False,      # フッターで回転させるか
    'use_seed': False,           # seedを使う
    'seed': datetime.today().strftime('%Y%m%d'), # seed値
    'prob_type': 'arithmetic',
}

# ------------------------
# 四則演算問題設定
# ------------------------
ARITH_SETTINGS = {
    'domain_arith': 'Z',         # 'N', 'Z', 'Q'
    'ops': {                     # 演算子のON/OFF
        '+': True,
        '-': False,
        '*': False,
        '/': False
    },
    'first_paren': False,        # 先頭の括弧
    'q_repr': 'frac',            # 'frac' or 'decimal'
    'frac': True,
    'decimal': False,
    'irreducible': False,        # 既約にする
    'decimal_places': 1,         # 小数桁数
    'n_terms': 2,                # 項数
    'use_custom': False,         # カスタム乱数
    'custom_ranges': [(-9, 9), (-9, 9), (-9, 9), (-9, 9)],
}

# ------------------------
# 展開問題設定
# ------------------------
EXPAND_SETTINGS = {
    'n_polys': 2,                # 多項式の数
    'monic': False,
    'min_terms': 2,
    'max_terms': 2,
    'var_type': '[x]',
    'var_set': 'x,y,z...',
    'domain_exp': 'Z',         # 'Z', 'Q'
    'first_minus': False,
}


DEFAULT_SETTINGS = {}
DEFAULT_SETTINGS.update(DOC_SETTINGS)
DEFAULT_SETTINGS.update(COMMON_SETTINGS)
DEFAULT_SETTINGS.update(ARITH_SETTINGS)
DEFAULT_SETTINGS.update(EXPAND_SETTINGS)


def get_settings_path():
    """標準の自動保存・自動読み込み用パス"""
    if getattr(sys, 'frozen', False):  # exe化された場合
        if platform.system() == "Darwin":  # macOS
            # ユーザーごとの設定保存場所
            base_dir = os.path.expanduser("~/.latexdearithmetics")
            os.makedirs(base_dir, exist_ok=True)
        else:
            # Windows/Linux は exe の隣でOK
            base_dir = os.path.dirname(sys.executable)
    else:  # 開発時
        base_dir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_dir, "settings.json")

def load_settings(path=None):
    """設定をロード（path未指定なら標準設定ファイルから）"""
    if path is None:
        path = get_settings_path()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_SETTINGS

def save_settings(settings: dict, path=None):
    """設定を保存（path未指定なら標準設定ファイルに）"""
    if path is None:
        path = get_settings_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
