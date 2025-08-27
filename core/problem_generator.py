import random
import fractions
from utils import format_number, max_2terms
from math import gcd


# ------------------------------
# RawFraction:
# ------------------------------
class RawFraction:
        """既約でない分数を保持する専用クラス"""
        def __init__(self, numerator, denominator):
                self.numerator = numerator
                self.denominator = denominator

        def __repr__(self):
                return f'RawFraction({self.numerator}, {self.denominator})'

        def __str__(self):
                return f'{self.numerator}/{self.denominator}'


# ------------------------------
# 値生成
# ------------------------------
def generate_value(settings, allow_zero=None):
    domain = settings['domain']
    if allow_zero is None:
        allow_zero = settings['allow_zero']
    q_repr = settings['q_repr']
    irreducible = settings['irreducible']
    decimal_places = int(settings['decimal_places'])
    min_val = int(settings['min_val'])
    max_val = int(settings['max_val'])
    
    """抽選リストから1つ選ぶ"""
    candidates = []
    if domain == 'N':
        # 全通り
        candidates = list(range(max(0, min_val), max_val + 1))
    elif domain == 'Z':
        # 全通り
        candidates = list(range(min_val, max_val + 1))
    elif domain == 'Q':
        # 分数で全通り
        numerators = list(range(min_val, max_val + 1))
        if not allow_zero:
            numerators = [x for x in numerators if x != 0]
        denominators = list(range(max(1, min_val), max_val + 1))
        for num in numerators:
            for denom in denominators:
                if q_repr == 'frac': # 分数
                    if irreducible:
                        frac = fractions.Fraction(num, denom)
                        if frac.denominator == 1:
                            frac = frac.numerator
                        candidates.append(frac)
                    else:
                        if denom == 1:
                            candidates.append(num)
                        else:
                            candidates.append(RawFraction(num, denom))
                else: # 小数
                    frac = fractions.Fraction(num, denom)
                    val = round(float(frac), decimal_places)
                    candidates.append(val)
    else:
        # N, Z, Q以外
        candidates = list(range(max(1, min_val), max_val + 1))

    if not allow_zero:
        candidates = [x for x in candidates if x != 0]

    # 候補がからの場合の保険
    if not candidates:
        if domain in ['N', 'Z']:
            return min_val
        elif domain == 'Q':
            return fractions.Fraction(min_val, 1)
        else:
            return min_val

    return random.choice(candidates)

def build_blocks(numbers, operators):
    """
    + / - で区切り、* / のみのブロックに分割
    返り値: (blocks, base_ops)
        blocks: [{'nums':[...], 'ops':[...]}...]
        base_ops: ブロック間の ['+','-','+','-'] の列
    """
    blocks = []
    base_ops = []
    current = {'nums': [], 'ops': []}

    for i, op in enumerate(operators):
        # まず i 番目の数を積む
        current['nums'].append(numbers[i])

        if op in ('*', '/'):
            current['ops'].append(op)
        else:
            # ブロック終了
            blocks.append(current)
            base_ops.append(op)    # ブロック間の + / -
            current = {'nums': [], 'ops': []}

    # 最後の数を積んでラストブロックを追加
    current['nums'].append(numbers[-1])
    blocks.append(current)
    return blocks, base_ops

def evaluate_block(block):
    """
    ブロックの評価
    - 除算が割り切れない場合、ブロック先頭の数（nums[0]）のみを最小限の倍率(割る数/GCD倍)で増やして割り切れるように調整
    返り値: (adjusted_block, block_value, block_expr_str)
    """

    nums = block['nums'][:]
    ops    = block['ops'][:]

    # 文字列を作るために、常に「調整後の nums[0]」を使って復元する
    adjusted_first = nums[0]
    current = adjusted_first

    # 演算を適用しながら、必要なら先頭を掛け増やして current にも反映
    for i, op in enumerate(ops):
        nxt = nums[i + 1]
        if op == '*':
            current *= nxt
        else:    # '/'
            # d = nxt if nxt != 0 else 1    # 念のため 0 除算防止（生成側で 0 は避けるが保険） <-数を1に更新しないといけない
            if nxt != 0:
                d = nxt
            else:
                d = 1
                nums[i + 1] = 1
            r = current % d
            if r != 0:
                k = abs(d // gcd(current, d)) # 整数でも使うためabsを追加
                adjusted_first *= k
                current *= k
            current //= d

    # 調整後の表現を作る（nums[0] を置き換えるだけ）
    expr_parts = [str(adjusted_first)]
    # cur_val = adjusted_first ???
    for i, op in enumerate(ops):
        n = nums[i + 1]
        expr_parts.append(op)
        expr_parts.append(str(n))
        # cur_val はすでに上で求めたが、ここでは式文字列のための結合
    block_expr = ''.join(expr_parts)

    # block 値は current
    adjusted_block = {'nums': [adjusted_first] + nums[1:], 'ops': ops}
    return adjusted_block, current, block_expr

def assemble_expr(blocks, base_ops, max_val, domain='N'):
    """
    ブロックの評価を左から足し引きし、減算で負になる場合は隣接ブロックを入れ替え、最初からやり直す。
    返り値: (expr_str, total_val)
    """
    # まず各ブロックを評価
    eval_blocks = []
    base_vals = []
    for blk in blocks:
        adj_blk, val, expr = evaluate_block(blk)
        eval_blocks.append({'block': adj_blk, 'expr': expr, 'val': val})
        base_vals.append(val)

    # 減算で負を出さないようにブロックを並べ替え
    if '-' in base_ops and domain == 'N':
        limit = 0
        while True:
            end_val = eval_blocks[0]['val']
            swapped = False
            for i, op in enumerate(base_ops):
                if op == '+':
                    end_val += eval_blocks[i + 1]['val']
                else:    # '-'
                    if end_val < eval_blocks[i + 1]['val']:
                        # 隣接ブロックを入れ替える価値があるか確認
                        if eval_blocks[i + 1] != eval_blocks[i]:
                            # 入れ替えて先頭からやり直し
                            eval_blocks[i], eval_blocks[i + 1] = eval_blocks[i + 1], eval_blocks[i]
                            base_vals[i], base_vals[i + 1] = base_vals[i + 1], base_vals[i]
                            swapped = True
                        else:
                            # 異なる数を探しに右へ走査
                            for j in range(i + 2, len(base_ops)):
                                if eval_blocks[i] != eval_blocks[j]:
                                    eval_blocks[j], eval_blocks[i] = eval_blocks[i], eval_blocks[j]
                                    base_vals[j], base_vals[i] = base_vals[i], base_vals[j]
                                    swapped = True
                                    break    # 走査 for を抜ける　
                    else:
                        end_val -= eval_blocks[i + 1]['val']
                if swapped:
                    break # while の先頭からやり直し
            
            limit += 1
            # swap不可能 or 無限ループ防止（ブロック数の2倍程度）
            if not swapped or limit > 2 * len(base_ops) + 5:
                # swapで解決できなかったので先頭ブロックを調整
                # 必要最小限～乱数最大値の範囲でランダムに増やす
                total = eval_blocks[0]['val']
                for i, op in enumerate(base_ops):
                    if op == '+':
                        total += eval_blocks[i + 1]['val']
                    else:
                        total -= eval_blocks[i + 1]['val']
                if total < 0:
                    add_val = eval_blocks[0]['val'] + abs(total)
                    if add_val <= max_val:
                        eval_blocks[0]['val'] = random.randint(add_val, max_val)
                    else:    
                        eval_blocks[0]['val'] += abs(total)
                    eval_blocks[0]['expr'] = f"{eval_blocks[0]['val']}"
                break

    # 最終式を組み立て & 合計値を算出
    expr_parts = [eval_blocks[0]['expr']]
    total = eval_blocks[0]['val']
    for i, op in enumerate(base_ops):
        expr_parts.append(op)
        expr_parts.append(eval_blocks[i + 1]['expr'])
        total += eval_blocks[i + 1]['val'] if op == '+' else -eval_blocks[i + 1]['val']
    expr = ' '.join(expr_parts)

    return expr, total

# ------------------------------
# 1問生成
# ------------------------------
def generate_one_problem(settings):
    num_problems = int(settings['num_problems'])
    n_terms = int(settings['n_terms'])
    domain = settings['domain']
    allow_zero = settings['allow_zero']
    allow_dup = settings['allow_dup']
    show_equal = settings['show_equal']
    ops = settings['ops'] # {'+': True, '-': False, ...}
    first_paren = settings['first_paren']
    q_repr = settings['q_repr']
    irreducible = settings['irreducible']
    decimal_places = int(settings['decimal_places'])
    min_val = int(settings['min_val'])
    max_val = int(settings['max_val'])

    selected_ops = [op for op, v in ops.items() if v]

    # --- 演算子を決定 ---
    operators = [random.choice(selected_ops) for _ in range(n_terms - 1)]

    # --- 数値生成 ---
    if domain == 'N':
        numbers = []
        for i in range(n_terms):
            # 直前が '/' のときは 0 を避ける
            if i > 0 and operators[i - 1] == '/':
                num = generate_value(settings, allow_zero=False)
            else:
                num = generate_value(settings, allow_zero=allow_zero)
            numbers.append(num)

        # ブロック化 → 評価（割り算調整）→ 減算回避の並べ替え
        blocks, base_ops = build_blocks(numbers, operators)
        expr, _total = assemble_expr(blocks, base_ops, max_val)

        return expr

    numbers = []
    if '/' in operators and domain in ['Z']:
        # / が含まれる場合の処理
        for idx in range(n_terms):
            # 直前が / の場合は 0 を避ける
            force_nonzero = (idx > 0 and operators[idx - 1] == '/')
            num = generate_value(
                settings,
                allow_zero=(allow_zero and not force_nonzero)
            )
            numbers.append(num)

        seg_start = 0 # 現在の割り算チェーンの分子となる項のインデックス
        for i, op in enumerate(operators):
            if op == '/':
                # 直前が/のとき
                divisor = numbers[i + 1]
                # セグメント先頭項に後続の除数を掛け込む
                numbers[seg_start] = numbers[seg_start] * divisor
            else:
                # 非'/'でセグメントをリセット
                seg_start = i + 1

    else:
        numbers = [generate_value(settings) for _ in range(n_terms)]

    # --- 式を組み立て ---
    expr = format_number(numbers[0], first_paren, is_first=True)
    for op, num in zip(operators, numbers[1:]):
        expr += f' {op} {format_number(num)}'
    return expr

def generate_problem_set(settings):
    num_problems = int(settings['num_problems'])
    allow_dup = settings['allow_dup']

    problems = []

    if allow_dup:
        for _ in range(num_problems):
            problems.append(generate_one_problem(settings))
    else:
        # 重複なし
        all_expr = set()
        while len(all_expr) < num_problems:
            expr = generate_one_problem(settings)
            all_expr.add(expr)
            # 無限ループ防止
            if len(all_expr) > 100000:
                raise ValueError('生成可能なユニーク問題数を超えています')
        problems = list(all_expr)
        
    return problems
