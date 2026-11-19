"""Dagster Definitions — wires the dlt + dbt + ML assets into one graph (ADR-010).

The daily schedule (run by the dagster-daemon, ADR-011) materialises the whole graph hands-off. The cron
is env-driven (`DP_SCHEDULE_CRON`, default 02:00 UTC) so a near-term cron can be used to verify the
scheduled-run path without waiting until the nightly tick.
"""
import os
from pathlib import Path

from dagster import DefaultScheduleStatus, Definitions, ScheduleDefinition, define_asset_job
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

from ktayl_orchestration import assets as a

DBT_DIR = Path(__file__).parent.parent / "dbt_demo"
dbt_project = DbtProject(project_dir=os.fspath(DBT_DIR))
dbt_project.prepare_if_dev()


@dbt_assets(manifest=dbt_project.manifest_path)
def dbt_models(context, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()


# the whole dlt → dbt → ML graph as one job, materialised daily by the daemon
all_assets_job = define_asset_job("all_assets_job", selection="*")

daily_refresh = ScheduleDefinition(
    name="daily_refresh",
    job=all_assets_job,
    cron_schedule=os.getenv("DP_SCHEDULE_CRON", "0 2 * * *"),  # 02:00 UTC nightly (overridable for tests)
    default_status=DefaultScheduleStatus.RUNNING,  # active on deploy — the daemon picks it up
)


defs = Definitions(
    assets=[a.raw_policy, dbt_models, a.policy_features, a.policy_model, a.model_evaluation],
    jobs=[all_assets_job],
    schedules=[daily_refresh],
    resources={"dbt": DbtCliResource(project_dir=os.fspath(DBT_DIR))},
)
