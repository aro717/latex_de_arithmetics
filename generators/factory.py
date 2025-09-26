from .arithmetic import ArithmeticGenerator
from .expand import ExpandGenerator

def generate_problem(settings):
    problem_type = settings.get("prob_type", "arithmetic")
    if problem_type == "arithmetic":
        return ArithmeticGenerator.generate_problem_set(settings)
    elif problem_type == "expand":
        return ExpandGenerator.generate_problem_set(settings)
    else:
        raise ValueError(f"Unknown problem_type: {problem_type}")
