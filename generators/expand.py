import random
from fractions import Fraction
from utils.fractions_utils import RawFraction
from .base import GeneratorBase


class ExpandGenerator(GeneratorBase):
    """
    多項式展開問題生成クラス
    """
    @classmethod
    def _generate(cls, settings):
        n_polys = settings.get('n_polys', 2)
        min_terms = settings.get('min_terms', 2)
        max_terms = settings.get('max_terms', 3)
        monic = settings.get('monic', False)
        first_minus = settings.get('first_minus', False)

        def generate_poly():
            """
            1つの多項式の係数リストを生成
            最高次項は monic=True なら 1 に固定
            """
            n_terms = random.randint(min_terms, max_terms)
            coef_list = []

            for i in range(n_terms):
                # 最高次項
                if i == 0 and monic:
                    coef = 1
                elif i == 0 and not first_minus:
                    coef = cls.generate_value(settings, allow_zero=False, term_idx=i, first_minus=False)
                else:
                    coef = cls.generate_value(settings, allow_zero=False, term_idx=i)
                coef_list.append(coef)

            return coef_list

        expr_values = [generate_poly() for _ in range(n_polys)]
        solve = cls.multiply(expr_values)

        return {
            'expr_values': expr_values,
            'solve': solve
        }

    @classmethod
    def generate_problem_set(cls, settings):
        """
        settings['num_problems'] に従い、複数問生成
        """
        num_problems = settings.get('num_problems', 10)
        allow_dup = settings.get('allow_dup', True)
        cls.init_random(settings)

        problems = []

        if allow_dup:
            for _ in range(num_problems):
                problems.append(cls._generate(settings))
        else:
            all_expr = set()
            while len(all_expr) < num_problems:
                data = cls._generate(settings)
                key = cls._freeze(data['expr_values'])
                if key not in all_expr:
                    all_expr.add(key)
                    problems.append(data)
                if len(all_expr) > 100000:
                    raise ValueError("生成可能なユニーク問題数を超えています")

        return problems

    def mul_as_fraction(a, b):
        """a, b を掛け算して Fraction で返す"""
        # RawFraction → Fraction に変換
        if isinstance(a, RawFraction):
            a = Fraction(a.numerator, a.denominator)
        if isinstance(b, RawFraction):
            b = Fraction(b.numerator, b.denominator)

        # int, float, Fraction 混在でも Fraction 化
        return Fraction(a) * Fraction(b)

    @classmethod
    def multiply(cls, expr_values):
        """
        expr_values を展開して掛け算結果の係数リストを返す
        （必要に応じて展開計算に利用可能）
        """
        from functools import reduce

        def poly_mult(p1, p2):
            """2つの多項式の掛け算（Fraction返却）"""
            deg1 = len(p1) - 1
            deg2 = len(p2) - 1
            result = [Fraction(0)] * (deg1 + deg2 + 1)
            for i, a in enumerate(p1):
                for j, b in enumerate(p2):
                    result[i + j] += cls.mul_as_fraction(a, b)
            return result

        return reduce(poly_mult, expr_values)
