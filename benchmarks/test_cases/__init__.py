"""Benchmark test cases for NorthStar evaluation."""

from benchmarks.test_cases.case_01_ecommerce_mvp import (
    CASE_NAME as CASE_01_NAME,
    GOALS as CASE_01_GOALS,
    TASKS as CASE_01_TASKS,
    EXPERT_RANKING as CASE_01_EXPERT_RANKING,
    EXPECTED_PDS_RANGE as CASE_01_EXPECTED_PDS_RANGE,
    DRIFT_SCENARIOS as CASE_01_DRIFT_SCENARIOS,
)
from benchmarks.test_cases.case_02_binance_integration import (
    CASE_NAME as CASE_02_NAME,
    GOALS as CASE_02_GOALS,
    TASKS as CASE_02_TASKS,
    EXPERT_RANKING as CASE_02_EXPERT_RANKING,
    EXPECTED_PDS_RANGE as CASE_02_EXPECTED_PDS_RANGE,
    DRIFT_SCENARIOS as CASE_02_DRIFT_SCENARIOS,
)
from benchmarks.test_cases.case_03_saas_conflict import (
    CASE_NAME as CASE_03_NAME,
    GOALS as CASE_03_GOALS,
    TASKS as CASE_03_TASKS,
    EXPERT_RANKING as CASE_03_EXPERT_RANKING,
    EXPECTED_PDS_RANGE as CASE_03_EXPECTED_PDS_RANGE,
    DRIFT_SCENARIOS as CASE_03_DRIFT_SCENARIOS,
)
from benchmarks.test_cases.case_04_technical_debt import (
    CASE_NAME as CASE_04_NAME,
    GOALS as CASE_04_GOALS,
    TASKS as CASE_04_TASKS,
    EXPERT_RANKING as CASE_04_EXPERT_RANKING,
    EXPECTED_PDS_RANGE as CASE_04_EXPECTED_PDS_RANGE,
    DRIFT_SCENARIOS as CASE_04_DRIFT_SCENARIOS,
)
from benchmarks.test_cases.case_05_pivot_scenario import (
    CASE_NAME as CASE_05_NAME,
    GOALS as CASE_05_GOALS,
    TASKS as CASE_05_TASKS,
    EXPERT_RANKING as CASE_05_EXPERT_RANKING,
    EXPECTED_PDS_RANGE as CASE_05_EXPECTED_PDS_RANGE,
    DRIFT_SCENARIOS as CASE_05_DRIFT_SCENARIOS,
)

ALL_CASES = [
    {
        "name": CASE_01_NAME,
        "goals": CASE_01_GOALS,
        "tasks": CASE_01_TASKS,
        "expert_ranking": CASE_01_EXPERT_RANKING,
        "expected_pds_range": CASE_01_EXPECTED_PDS_RANGE,
        "drift_scenarios": CASE_01_DRIFT_SCENARIOS,
    },
    {
        "name": CASE_02_NAME,
        "goals": CASE_02_GOALS,
        "tasks": CASE_02_TASKS,
        "expert_ranking": CASE_02_EXPERT_RANKING,
        "expected_pds_range": CASE_02_EXPECTED_PDS_RANGE,
        "drift_scenarios": CASE_02_DRIFT_SCENARIOS,
    },
    {
        "name": CASE_03_NAME,
        "goals": CASE_03_GOALS,
        "tasks": CASE_03_TASKS,
        "expert_ranking": CASE_03_EXPERT_RANKING,
        "expected_pds_range": CASE_03_EXPECTED_PDS_RANGE,
        "drift_scenarios": CASE_03_DRIFT_SCENARIOS,
    },
    {
        "name": CASE_04_NAME,
        "goals": CASE_04_GOALS,
        "tasks": CASE_04_TASKS,
        "expert_ranking": CASE_04_EXPERT_RANKING,
        "expected_pds_range": CASE_04_EXPECTED_PDS_RANGE,
        "drift_scenarios": CASE_04_DRIFT_SCENARIOS,
    },
    {
        "name": CASE_05_NAME,
        "goals": CASE_05_GOALS,
        "tasks": CASE_05_TASKS,
        "expert_ranking": CASE_05_EXPERT_RANKING,
        "expected_pds_range": CASE_05_EXPECTED_PDS_RANGE,
        "drift_scenarios": CASE_05_DRIFT_SCENARIOS,
    },
]
