"""minicloud Data Platform — system-design / workflow view (diagram-as-code).

mingrammer `diagrams` + Graphviz. Self-contained; lives with the data-platform docs. Shows the end-to-end
workflow built across ADR-006/007/008 (lake + warehouse), ADR-009 (Cube semantic layer) and ADR-010
(dlt + Dagster + ML). Facts from the ADRs + the live manifests (minicloud-gitops platform/data/data-platform).

Run:  python data_platform_workflow.py   (needs: pip install diagrams ; brew/apt install graphviz)
Out:  ../architecture/img/data-platform-workflow.{png,svg}
"""
from __future__ import annotations

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.custom import Custom
from diagrams.onprem.analytics import Dbt, Metabase
from diagrams.onprem.client import Users
from diagrams.onprem.compute import Server
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.mlops import Mlflow
from diagrams.onprem.workflow import Airflow
from diagrams.aws.storage import S3
from diagrams.programming.language import Python

# ----------------------------------------------------------------- theme (inlined, house style)
SLATE, CYAN, GREEN, TEXT, MUTED, AMBER = "#0f172a", "#22d3ee", "#34d399", "#e2e8f0", "#94a3b8", "#f59e0b"
ICONS = Path(__file__).resolve().parent / "icons"
OUT = Path(__file__).resolve().parent.parent / "architecture" / "img"
OUT.mkdir(parents=True, exist_ok=True)


def node(cls, label, icon=None):
    p = ICONS / icon if icon else None
    return Custom(label, str(p)) if p and p.exists() else cls(label)


def cl(pencolor=CYAN):
    return {"bgcolor": "#111c33", "pencolor": pencolor, "fontcolor": pencolor,
            "fontname": "Helvetica-Bold", "fontsize": "13", "style": "rounded", "penwidth": "1.6"}


GRAPH = {"bgcolor": SLATE, "fontcolor": TEXT, "fontname": "Helvetica", "fontsize": "20",
         "pad": "0.6", "nodesep": "0.5", "ranksep": "1.0", "splines": "spline"}
NODE = {"fontcolor": TEXT, "fontname": "Helvetica", "fontsize": "11"}
EDGE = {"color": MUTED, "fontcolor": MUTED, "fontname": "Helvetica", "fontsize": "9"}


def flow(label=""):
    return Edge(label=label, color=CYAN, fontcolor=MUTED)


def serve(label=""):
    return Edge(label=label, color=GREEN, fontcolor=MUTED)


def orch(label=""):
    return Edge(label=label, color=AMBER, fontcolor=MUTED, style="dashed")


with Diagram(
    "minicloud Data Platform — workflow  ·  sources → dlt → lake → dbt → CNPG → Cube → BI + ML",
    filename=str(OUT / "data-platform-workflow"),
    outformat=["png", "svg"],
    direction="LR",
    show=False,
    graph_attr=GRAPH,
    node_attr=NODE,
    edge_attr=EDGE,
):
    # ---- consumers (right) ----
    analyst = Users("Analyst / PO\nAuthentik SSO")

    # ---- sources (left) ----
    with Cluster("Operational sources  ·  IS business apps", graph_attr=cl(MUTED)):
        core = Server("ktayl-core\npolicy.policy (CNPG)")
        uw = Server("Underwriting\nquote/binding (CNPG)")

    # ---- ingest ----
    with Cluster("Ingest  ·  dlt (ADR-010)  +  producer (ADR-008)", graph_attr=cl(CYAN)):
        dlt = node(Python, "dlt pipeline\nsql_table → schema-inferred\n(replaces COPY scripts)")

    # ---- lake ----
    with Cluster("Raw lake  ·  AWS S3 (eu-west-1)  ·  Vault-STS keyless", graph_attr=cl(AMBER)):
        s3 = S3("S3 raw\nParquet · versioned · SSE")

    # ---- transform ----
    with Cluster("Transform  ·  OLAP (storage/compute split)", graph_attr=cl(CYAN)):
        duck = node(Python, "DuckDB\nhttpfs — reads Parquet")
        dbt = Dbt("dbt (duckdb/postgres)\nstaging → curated → marts\n+ MDM dims + fact_policy")

    # ---- serving warehouse ----
    with Cluster("Serving  ·  CloudNativePG (analytics)", graph_attr=cl(GREEN)):
        cnpg = PostgreSQL("CNPG gold marts\nbusiness.* · lake.* · dlt_marts.*")

    # ---- semantic + BI + ML ----
    with Cluster("Semantic + consumption", graph_attr=cl(GREEN)):
        cube = node(Server, "Cube (ADR-009)\nsemantic layer\nSQL API · REST/GraphQL")
        metabase = Metabase("Metabase\nBI dashboards")
        mlflow = Mlflow("MLflow\ntracking + model registry")

    # ---- orchestration (spans the pipeline) ----
    with Cluster("Orchestration  ·  Dagster (ADR-010)  ·  asset graph + lineage UI", graph_attr=cl(AMBER)):
        dagster = Airflow("Dagster\ndlt + dbt + ML as one asset graph")

    # ---- data flow (principal) ----
    core >> flow("read-only\n(analytics_ro)") >> dlt
    uw >> flow() >> dlt
    dlt >> flow("land Parquet") >> s3
    s3 >> flow("read (httpfs)") >> duck
    duck >> flow() >> dbt
    dbt >> flow("materialise marts") >> cnpg

    # ---- serving ----
    cnpg >> serve("SQL") >> cube
    cube >> serve("pg-wire SQL API") >> metabase
    metabase >> serve("HTTPS · SSO") >> analyst
    cnpg >> serve("features") >> mlflow

    # ---- orchestration (Dagster drives + observes the assets) ----
    dagster >> orch("materialise + lineage") >> dlt
    dagster >> orch() >> dbt
    dagster >> orch("train → register") >> mlflow
