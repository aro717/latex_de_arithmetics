import random
from fractions import Fraction
from utils.utils import build_blocks, paren_if_negative
from utils.fractions_utils import RawFraction
from math import gcd
from .base import GeneratorBase


class ArithmeticGenerator(GeneratorBase):
    """
    四則演算問題生成クラス
    """
    @classmethod
    def evaluate_block(cls, block):
        """
        ブロックの評価
        - 除算が割り切れない場合、ブロック先頭の数（nums[0]）のみを最小限の倍率(割る数/GCD倍)で増やして割り切れるように調整
        返り値: (adjusted_block, block_value, block_expr_str)
        """
        nums = block['nums'][:]
        ops = block['ops'][:]
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
        for i, op in enumerate(ops):
            n = nums[i + 1]
            expr_parts.append(op)
            expr_parts.append(str(n))
        block_expr = ''.join(expr_parts)

        # block 値は current
        adjusted_block = {'nums': [adjusted_first] + nums[1:], 'ops': ops}
        return adjusted_block, current, block_expr

    @classmethod
    def assemble_expr(cls, blocks, base_ops, max_val, domain='N'):
        """
        ブロックの評価を左から足し引きし、減算で負になる場合は隣接ブロックを入れ替え、最初からやり直す。
        返り値: (expr_str, total_val)
        """
        # まず各ブロックを評価
        eval_blocks = []
        base_vals = []
        for blk in blocks:
            adj_blk, val, expr = cls.evaluate_block(blk)
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
        
        vals = []
        for block in eval_blocks:
            for i in block['block']['nums']:
                vals.append(i)
        
        return expr, vals, total

    @classmethod
    # --- 1問生成 ---
    def _generate(cls, settings):
        n_terms = int(settings['n_terms'])
        domain = settings['domain_arith']
        allow_zero = settings['allow_zero']
        selected_ops = [op for op, v in settings['ops'].items() if v]
        first_paren = settings['first_paren']
        max_val = max(max_i for (_, max_i) in settings['custom_ranges'])

        # --- 演算子を決定 ---
        operators = [random.choice(selected_ops) for _ in range(n_terms - 1)]

        numbers = []

        # --- 数値生成 ---
        if domain == 'N':
            for i in range(n_terms):
                # 直前が '/' のときは 0 を避ける
                if i > 0 and operators[i - 1] == '/':
                    num = cls.generate_value(settings, allow_zero=False, term_idx=i)
                else:
                    num = cls.generate_value(settings, allow_zero=allow_zero, term_idx=i)
                numbers.append(num)
        elif domain == 'Z':
        # if '/' in operators and domain in ['Z']:
            # / が含まれる場合の処理
            for i in range(n_terms):
                # 直前が / の場合は 0 を避ける
                force_nonzero = (i > 0 and operators[i - 1] == '/')
                num = cls.generate_value(settings, allow_zero=(allow_zero and not force_nonzero), term_idx=i)
                numbers.append(num)
            # 割り算チェーン調整
            seg_start = 0
            for i, op in enumerate(operators):
                if op == '/':
                    # 直前が/のとき
                    divisor = numbers[i + 1]
                    # セグメント先頭項に後続の除数を掛け込む
                    numbers[seg_start] = numbers[seg_start] * divisor
                else:
                    # 非'/'でセグメントをリセット
                    seg_start = i + 1
        elif domain == 'Q':
            for i in range(n_terms):
                # 直前が / の場合は 0 を避ける
                force_nonzero = (i > 0 and operators[i - 1] == '/')
                num = cls.generate_value(settings, allow_zero=(allow_zero and not force_nonzero), term_idx=i)
                numbers.append(num)
        else:
            numbers = [cls.generate_value(settings) for _ in range(n_terms)]

        if domain in ['N', 'Z']:
            # ブロック化 → 評価（割り算調整）→ 減算回避の並べ替え
            blocks, base_ops = build_blocks(numbers, operators)
            expr_str, numbers, total = cls.assemble_expr(blocks, base_ops, max_val, domain)
        else:
            # Q や他のドメインは単純連結
            expr_str = paren_if_negative(numbers[0], first_paren, is_first=True)
            total = numbers[0]
            if isinstance(total, RawFraction):
                total = Fraction(num.numerator, num.denominator)
            for op, num in zip(operators, numbers[1:]):
                if isinstance(num, RawFraction):
                    num = Fraction(num.numerator, num.denominator)
                expr_str += f' {op} {paren_if_negative(num)}'
                if op == '+':
                    total += num
                elif op == '-':
                    total -= num
                elif op == '*':
                    total *= num
                elif op == '/':
                    total /= num

        return {
            'vals_ops': [numbers, operators],
            'solve': total
        }

    @classmethod
    def generate_problem_set(cls, settings):
        num_problems = int(settings['num_problems'])
        allow_dup = settings['allow_dup']
        cls.init_random(settings)

        problems = []

        if allow_dup:
            for _ in range(num_problems):
                problems.append(cls._generate(settings))
        else:
            # 重複なし
            all_expr = set()
            while len(all_expr) < num_problems:
                data = cls._generate(settings)
                key = cls._freeze(data['vals_ops'])
                if key not in all_expr:
                    all_expr.add(key)
                    problems.append(data)
                # 無限ループ防止
                if len(all_expr) > 100000:
                    raise ValueError('生成可能なユニーク問題数を超えています')
            # problems = list(all_expr)
            
        return problems
