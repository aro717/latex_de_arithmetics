import fractions

decimal_places = 2 # デフォルト

def format_number(value, first_paren=False, is_first=False):
    """負数は括弧付きにして返す"""
    if isinstance(value, int): # 整数
      return f'({value})' if value < 0 and (first_paren or not is_first) else str(value)

    elif isinstance(value, fractions.Fraction): # 分数(既約)
      num, denom = value.numerator, value.denominator
      if num < 0 and (first_paren or not is_first):
          return f'(-\\frac{{{abs(num)}}}{{{denom}}})'
      else:
          return f'\\frac{{{num}}}{{{denom}}}'

    elif hasattr(value, 'numerator') and hasattr(value, 'denominator'):
      num, denom = value.numerator, value.denominator
      if num < 0:
        return f'-\\frac{{{abs(num)}}}{{{denom}}}' if is_first else f'(-\\frac{{{abs(num)}}}{{{denom}}})'
      else:
        return f'\\frac{{{num}}}{{{denom}}}'

    elif isinstance(value, float):  # 小数
      val = round(value, decimal_places)
      return f'({val})' if val < 0 and (first_paren or not is_first) else f'{val}'

    else:
      return str(value)

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

def number_to_latex(value, first_paren=False, is_first=False, decimal_places=2):
    """
    数値・Fraction・RawFraction を LaTeX 表記に変換
    - 負数はトップレベルで外にマイナス
    - Fraction は \frac{num}{denom} 形式
    - float は小数点以下 decimal_places で丸め
    """
    # 整数
    if isinstance(value, int):
        if value < 0 and (first_paren or not is_first):
            return f'({value})'
        else:
            return str(value)

    # Fraction / RawFraction
    elif hasattr(value, 'numerator') and hasattr(value, 'denominator'):
        num, denom = value.numerator, value.denominator
        if num < 0:
            if first_paren or not is_first:
                return f'(-\\frac{{{abs(num)}}}{{{denom}}})'
            else:
                return f'-\\frac{{{abs(num)}}}{{{denom}}}'
        else:
            return f'\\frac{{{num}}}{{{denom}}}'

    # float
    elif isinstance(value, float):
        val = round(value, decimal_places)
        if val < 0 and (first_paren or not is_first):
            return f'({val})'
        else:
            return str(val)

    # その他
    else:
        return str(value)


def text_to_latex(expr_text):
    r"""
    Textビューの式を LaTeX 形式に変換
    - × -> \times
    - ÷ -> \div
    - すでに \frac{}{} 形式の分数はそのまま
    """
    latex = expr_text.replace('×', r'\times').replace('÷', r'\div')
    return latex
