from .arithmetic import ArithmeticProblem
from .expand import ExpandProblem

def make_problem(data, settings):
    prob_type = settings.get("prob_type", "arithmetic")
    if prob_type == "arithmetic":
        return ArithmeticProblem(data, settings)
    elif prob_type == "expand":
        return ExpandProblem(data, settings)
    else:
        raise ValueError(f"Unknown prob_type: {prob_type}")
