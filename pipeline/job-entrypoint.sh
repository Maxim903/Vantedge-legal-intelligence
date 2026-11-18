#!/bin/sh
set -eu

read_secret() {
  test -s "$1" || { echo "Secret absent ou vide : $1" >&2; exit 1; }
  cat "$1"
}

job=$1
shift
case "$job" in
  extract-entities)
    LLM_API_KEY=$(read_secret /secrets/llm/key)
    export LLM_API_KEY
    ;;
  collect-volumes)
    DATAFORSEO_LOGIN=$(read_secret /secrets/dataforseo/login)
    DATAFORSEO_PASSWORD=$(read_secret /secrets/dataforseo/password)
    export DATAFORSEO_LOGIN DATAFORSEO_PASSWORD
    ;;
  sync-graph)
    NEO4J_URI=$(read_secret /secrets/neo4j/uri)
    NEO4J_USER=$(read_secret /secrets/neo4j/user)
    NEO4J_PASSWORD=$(read_secret /secrets/neo4j/password)
    export NEO4J_URI NEO4J_USER NEO4J_PASSWORD
    exec python -m graph "$@"
    ;;
  dbt)
    exec dbt build --project-dir /app/dbt --profiles-dir /app/dbt "$@"
    ;;
  load-corpus|load-raw-market) ;;
  *) echo "Job inconnu : $job" >&2; exit 2 ;;
esac
exec python -m vil_pipeline.cli "$job" "$@"
