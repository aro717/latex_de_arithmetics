import random
from abc import ABC, abstractmethod
from fractions import Fraction
from utils.fractions_utils import RawFraction


class GeneratorBase(ABC):
    """
    問題生成専用の抽象基底クラス
    """
    def __init__(self, expr_values=None, operators=None, total=None):
        self.expr_values = expr_values or []
        self.operators = operators or []
        self.total = total

    @classmethod
    @abstractmethod
    def generate(cls, settings):
        """
        settings に基づき問題を生成してProblemBaseインスタンスを返す
        """
        pass

    @staticmethod
    def init_random(settings):
        """乱数の初期化（seed値がある場合のみ）"""
        if settings.get('use_seed'):
            seed = settings.get('seed')
            if seed:
                try:
                    random.seed(int(seed))  # 数値に変換
                except ValueError:
                    random.seed(seed)       # 文字列でもOK
    
    @staticmethod
    def generate_value(settings, allow_zero=None, term_idx=None, first_minus=True):
        """
        term_idx: int, 各項のカスタム範囲を使う場合に項番号を指定
        """
        if settings['prob_type'] == 'arithmetic':
            domain = settings['domain_arith']
        elif settings['prob_type'] == 'expand':
            domain = settings['domain_exp']
        if allow_zero is None:
            allow_zero = settings['allow_zero']
        q_repr = settings['q_repr']
        irreducible = settings['irreducible']
        decimal_places = int(settings['decimal_places'])

        if term_idx is None:
            min_val = int(settings['min_val'])
            max_val = int(settings['max_val'])
        else:
            min_val, max_val = settings['custom_ranges'][term_idx]
            min_val, max_val = int(min_val), int(max_val)

        if not first_minus:
            min_val = max(0, min_val)
            max_val = max(0, max_val)
        
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
                if num == 0:
                    # 分母に関係なく 0 は一度だけ追加
                    candidates.append(0)
                    continue
                for denom in denominators:
                    if q_repr == 'frac': # 分数
                        if irreducible:
                            frac = Fraction(num, denom)
                            if frac.denominator == 1:
                                frac = frac.numerator
                            candidates.append(frac)
                        else:
                            if denom == 1:
                                candidates.append(num)
                            else:
                                candidates.append(RawFraction(num, denom))
                    else: # 小数
                        frac = Fraction(num, denom)
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
                return Fraction(min_val, 1)
            else:
                return min_val

        return random.choice(candidates)

    @classmethod
    def _freeze(cls, obj):
        """
        ネストした list/dict/tuple や数値等をハッシュ可能かつ型を区別する形に正規化して返す。
        例: 1 -> ('int', 1), 1.0 -> ('float', 1.0), Fraction(1,2) -> ('Fraction', 1, 2)
        """
        # list / tuple: 再帰的に処理して tuple に
        if isinstance(obj, list) or isinstance(obj, tuple):
            return tuple(cls._freeze(x) for x in obj)

        # dict: キー順にソートして (k, freeze(v)) のタプル列に
        if isinstance(obj, dict):
            return tuple((k, cls._freeze(v)) for k, v in sorted(obj.items()))

        # RawFraction: to_fraction() して分子分母で表現
        if isinstance(obj, RawFraction):
            f = obj.to_fraction()
            return ('Fraction', int(f.numerator), int(f.denominator))

        # fractions.Fraction: 分子分母で表現
        if isinstance(obj, Fraction):
            return ('Fraction', int(obj.numerator), int(obj.denominator))

        # 文字列やブールは型タグ付きで
        if isinstance(obj, str):
            return ('str', obj)
        if isinstance(obj, bool):
            return ('bool', obj)

        # int / float / その他数値: 明示的に型名を付ける（1 と 1.0 を別にするため）
        if isinstance(obj, int) and not isinstance(obj, bool):
            return ('int', obj)
        if isinstance(obj, float):
            return ('float', obj)
        if isinstance(obj, numbers.Number):
            # その他の数値型（Decimal など）は型名+reprで保持
            return (type(obj).__name__, repr(obj))

        # その他の任意オブジェクトは型名と repr で保険をかける
        return (type(obj).__name__, repr(obj))
