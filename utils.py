from fractions_utils import RawFraction

decimal_places = 2 # デフォルト

def max_2terms(min_val:int, max_val:int, ops:list[str], domain:str, allow_zero:bool) -> int:
    """
    2項全パターン計算
    """
    count = 0
    
    if domain == 'N':
        n_x1 = max_val - max(0, min_val) + 1
    else:
        n_x1 = max_val - min_val + 1

    if not allow_zero:
        n_x1 -= 1
    
    for op in ops:
        if op == '-':
            if domain == 'N':
                count += n_x1 * (n_x1 + 1) // 2
            elif domain == 'Z':
                count += n_x1 ** 2
        elif op == '/':
            if min_val <= 0:
                count += n_x1 * (n_x1 - 1)
            else:
                count += n_x1 ** 2
        else:
            count += n_x1 ** 2
    
    return count

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

def value_as_fraction(val):
    if isinstance(val, RawFraction):
        return val.to_fraction()
    return val

def evaluate_blocks(blocks, base_ops):
    """
    +-で分けたblock毎の評価をし、左から+-する
    """
    blocks_values = []
    for blk in blocks:
        current = value_as_fraction(blk['nums'][0])
        for i, op in enumerate(blk['ops']):
            nxt = value_as_fraction(blk['nums'][i + 1])
            if op == '*':
                current *= nxt
            else:
                current /= nxt
        blocks_values.append(current)
    total = blocks_values[0]
    for i, op in enumerate(base_ops):
        if op == '+':
            total += blocks_values[i + 1]
        else:
            total -= blocks_values[i + 1]

    return total

def dict_diff(old: dict, new: dict) -> dict:
    """
    2つのdictの差分を {キー: (old_value, new_value)} の形で返す
    """
    return {
        k: (old.get(k), new.get(k))
        for k in new.keys() | old.keys()  # 両方にあるキーの和集合
        if old.get(k) != new.get(k)
    }

def resource_path(relative_path):
    """appでも正しく参照できるパスを返す"""
    if getattr(sys, 'frozen', False):
        # PyInstaller バンドル内
        base_path = os.path.dirname(sys.executable)
    else:
        # 通常の Python 実行
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)
