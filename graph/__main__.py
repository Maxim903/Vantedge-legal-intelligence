"""Run the marts-to-Neo4j synchronization."""

import argparse
import os

from google.cloud import bigquery
from neo4j import GraphDatabase

from graph.sync import sync_graph


def main() -> None:
    parser = argparse.ArgumentParser(description="Synchronise les marts vers Neo4j.")
    parser.add_argument("--project-id", default=os.environ.get("GCP_PROJECT_ID"))
    parser.add_argument("--dataset", default="marts")
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()
    if not args.project_id:
        parser.error("--project-id ou GCP_PROJECT_ID est obligatoire")
    if args.batch_size < 1:
        parser.error("--batch-size doit être supérieur à zéro")

    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER")
    password = os.environ.get("NEO4J_PASSWORD")
    if not uri or not user or not password or not all(
        value.strip() for value in (uri, user, password)
    ):
        parser.error("NEO4J_URI, NEO4J_USER et NEO4J_PASSWORD sont obligatoires")
    with (
        bigquery.Client(
            project=args.project_id, location=os.environ.get("BQ_LOCATION")
        ) as client,
        GraphDatabase.driver(uri, auth=(user, password)) as driver,
    ):
        stats = sync_graph(
            driver, client, bigquery.DatasetReference(args.project_id, args.dataset),
            batch_size=args.batch_size,
        )
    print(
        f"Synchronisation : lot {stats.run_id}, nœuds {stats.node_rows}, "
        f"relations {stats.relation_rows}, lots {stats.batches}."
    )


if __name__ == "__main__":
    main()
