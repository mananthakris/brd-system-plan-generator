from .check_plan_generator import ALL_CHECKS as PLAN_CHECKS
from .check_schedule_estimator import ALL_CHECKS as SCHEDULE_CHECKS
from .check_solution_architect import ALL_CHECKS as ARCHITECT_CHECKS
from .check_tech_stack_recommender import ALL_CHECKS as TECH_STACK_CHECKS
from .check_critic import ALL_CHECKS as CRITIC_CHECKS
from .check_formatter import ALL_CHECKS as FORMATTER_CHECKS

CHECKS_BY_AGENT: dict[str, list] = {
    "plan_generator": PLAN_CHECKS,
    "schedule_estimator": SCHEDULE_CHECKS,
    "solution_architect": ARCHITECT_CHECKS,
    "tech_stack_recommender": TECH_STACK_CHECKS,
    "critic": CRITIC_CHECKS,
    "output_formatter": FORMATTER_CHECKS,
}
