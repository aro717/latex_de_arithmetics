import os
import sys
import platform
import json
from datetime import datetime

MAX_TERMS = 4

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
    'title_check': False,
    'title': 'LaTeX de Arithmetics',                 # 表題
    'date_check': False,
    'date': '',                  # 日付 YYYY/MM/DD
    'name_check': False,
    'name': r'組\hspace{10mm}番\ 氏名(\hspace{50mm})', # 氏名
}

# ------------------------
# 四則演算問題設定
# ------------------------
ARITH_SETTINGS = {
    'num_problems': 48,          # 問題数
    'cols': 4,                   # 列数
    'domain': 'N',               # 'N', 'Z', 'Q'
    'allow_zero': False,         # 0を許容
    'allow_dup': False,          # 重複許可
    'show_equal': True,          # =表示
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
    'decimal_places': 2,         # 小数桁数
    'n_terms': 2,                # 項数
    'min_val': 1,                # 値の最小
    'max_val': 9,                # 値の最大
    'use_custom': False,         # カスタム乱数
    'custom_ranges': [(1, 9), (1, 9), (1, 9), (1, 9)],
    'show_answer': False,        # 解答表示
    'answer_pos': 'new_page',    # 表示場所
    'ans_new_page': True,
    'ans_footer': False,
    'footer_rotate': False,      # フッターで回転させるか
    'use_seed': False,           # seedを使う
    'seed': datetime.today().strftime('%Y%m%d'), # seed値
}

# ------------------------
# 展開問題設定
# ------------------------
EXPAND_SETTINGS = {
    'poly_num': 2                # 多項式の数
}


DEFAULT_SETTINGS = {}
DEFAULT_SETTINGS.update(DOC_SETTINGS)
DEFAULT_SETTINGS.update(ARITH_SETTINGS)
DEFAULT_SETTINGS.update(EXPAND_SETTINGS)


def get_settings_path():
    if getattr(sys, 'frozen', False):  # exe化された場合
        if platform.system() == "Darwin":  # macOS
            # ユーザーごとの設定保存場所
            base_dir = os.path.expanduser("~/.latexdearithmetics")
            os.makedirs(base_dir, exist_ok=True)
        else:
            # Windows/Linux は exe の隣でOK
            base_dir = os.path.dirname(sys.executable)
    else:  # 開発中
        base_dir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_dir, "settings.json")

def load_settings():
    path = get_settings_path()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_SETTINGS

def save_settings(settings: dict):
    path = get_settings_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
