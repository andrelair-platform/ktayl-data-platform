"""Dagster assets — the modern self-hosted data+ML stack as ONE asset graph (ADR-010).

    raw_policy (dlt ingest)  →  portfolio (dbt transform)  →  policy_features → policy_model → model_evaluation
    └ ktayl-core policy.policy    └ analytics.dlt_marts          └ pandas          └ sklearn+MLflow   └ MLflow metric

- Ingest:    dlt (replaces the hand-written COPY/DuckDB scripts) — sql_table(ktayl-core) → CNPG analytics.dlt_raw.
- Transform: dbt (dagster-dbt, one asset per model) — dlt_raw.policy → dlt_marts.portfolio.
- ML:        scikit-learn trained on the portfolio, tracked + registered in the platform's MLflow.

Everything is env-config (12-factor). The ML model is a DEMO/plumbing proof on tiny data — it proves the
train→track→register→evaluate path + lineage, not a production model.
"""
import os

import dlt
import mlflow
import pandas as pd
from dagster import AssetExecutionContext, AssetKey, MetadataValue, asset
from dlt.sources.sql_database import sql_table
from sqlalchemy import create_engine


def _analytics_url() -> str:
    return (
        f"postgresql://{os.environ['ANALYTICS_PG_USER']}:{os.environ['ANALYTICS_PG_PASSWORD']}"
        f"@{os.environ['ANALYTICS_PG_HOST']}:5432/{os.environ['ANALYTICS_PG_DB']}"
    )


# ── 1. INGEST (dlt) ────────────────────────────────────────────────────────────
@asset(compute_kind="dlt", group_name="ingest")
def raw_policy(context: AssetExecutionContext) -> None:
    """dlt pipeline: ktayl-core policy.policy → CNPG analytics.dlt_raw.policy (schema-inferred, full refresh)."""
    source = sql_table(
        credentials=(
            f"postgresql://{os.environ['SOURCE_PG_USER']}:{os.environ['SOURCE_PG_PASSWORD']}"
            f"@{os.environ['SOURCE_PG_HOST']}:5432/{os.environ['SOURCE_PG_DB']}"
        ),
        schema="policy",
        table="policy",
    )
    pipeline = dlt.pipeline(
        pipeline_name="ktayl_policy",
        destination=dlt.destinations.postgres(_analytics_url()),
        dataset_name="dlt_raw",
        progress=None,
    )
    info = pipeline.run(source, write_disposition="replace")
    rows = pd.read_sql("select count(*) n from dlt_raw.policy", create_engine(_analytics_url())).n.iloc[0]
    context.add_output_metadata({"rows_landed": MetadataValue.int(int(rows)), "dlt_load": str(info)})


# ── 3. ML (depends on the dbt `portfolio` asset) ────────────────────────────────
# dagster-dbt prefixes the model's custom schema into the asset key → ["dlt_marts","portfolio"].
@asset(deps=[AssetKey(["dlt_marts", "portfolio"])], compute_kind="pandas", group_name="ml")
def policy_features(context: AssetExecutionContext) -> pd.DataFrame:
    """Read the dbt portfolio mart into a feature frame (one-hot product_code + year + size)."""
    df = pd.read_sql("select * from dlt_marts.portfolio", create_engine(_analytics_url()))
    df["is_mostly_active"] = (df["active_count"] / df["policy_count"].clip(lower=1) >= 0.5).astype(int)
    context.add_output_metadata({"feature_rows": MetadataValue.int(len(df))})
    return df


@asset(compute_kind="sklearn", group_name="ml")
def policy_model(context: AssetExecutionContext, policy_features: pd.DataFrame) -> str:
    """DEMO model: predict 'mostly active' from product/year/size. Trained + registered in MLflow."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import OneHotEncoder
    from sklearn.compose import ColumnTransformer
    from sklearn.pipeline import Pipeline

    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    mlflow.set_experiment("ktayl-policy-portfolio-demo")

    X = policy_features[["product_code", "inception_year", "policy_count"]]
    y = policy_features["is_mostly_active"]
    pre = ColumnTransformer(
        [("oh", OneHotEncoder(handle_unknown="ignore"), ["product_code"])], remainder="passthrough"
    )
    model = Pipeline([("pre", pre), ("clf", LogisticRegression(max_iter=1000))])

    with mlflow.start_run(run_name="policy-active-demo") as run:
        model.fit(X, y)
        mlflow.log_param("n_samples", len(X))
        mlflow.log_param("features", "product_code,inception_year,policy_count")
        mlflow.sklearn.log_model(model, "model", registered_model_name="ktayl-policy-active-demo")
        uri = f"runs:/{run.info.run_id}/model"
    context.add_output_metadata({"mlflow_run": run.info.run_id, "model_uri": uri})
    return uri


@asset(compute_kind="sklearn", group_name="ml")
def model_evaluation(
    context: AssetExecutionContext, policy_model: str, policy_features: pd.DataFrame
) -> None:
    """Score the demo model (train accuracy — toy data) and log the metric to MLflow."""
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    model = mlflow.sklearn.load_model(policy_model)
    X = policy_features[["product_code", "inception_year", "policy_count"]]
    y = policy_features["is_mostly_active"]
    acc = float((model.predict(X) == y).mean())
    with mlflow.start_run(run_name="policy-active-demo-eval"):
        mlflow.log_metric("train_accuracy", acc)
    context.add_output_metadata({"train_accuracy": MetadataValue.float(acc)})
