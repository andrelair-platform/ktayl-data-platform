"""Dagster Definitions — wires the dlt + dbt + ML assets into one graph (ADR-010)."""
import os
from pathlib import Path

from dagster import Definitions
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

from ktayl_orchestration import assets as a

DBT_DIR = Path(__file__).parent.parent / "dbt_demo"
dbt_project = DbtProject(project_dir=os.fspath(DBT_DIR))
dbt_project.prepare_if_dev()


@dbt_assets(manifest=dbt_project.manifest_path)
def dbt_models(context, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()


defs = Definitions(
    assets=[a.raw_policy, dbt_models, a.policy_features, a.policy_model, a.model_evaluation],
    resources={"dbt": DbtCliResource(project_dir=os.fspath(DBT_DIR))},
)
