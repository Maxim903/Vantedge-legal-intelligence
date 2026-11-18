"""Apply the explicitly defined Neo4j uniqueness constraints."""

import os
import re
from pathlib import Path

from neo4j import Driver, GraphDatabase

DEFAULT_CONSTRAINTS_FILE = (
    Path(__file__).resolve().parents[4] / "graph" / "constraints.cypher"
)

_CONSTRAINT = re.compile(
    r"CREATE\s+CONSTRAINT\s+[A-Za-z_][A-Za-z0-9_]*\s+IF\s+NOT\s+EXISTS\s+"
    r"FOR\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*\)\s+REQUIRE\s+\1\."
    r"([A-Za-z_][A-Za-z0-9_]*)\s+IS\s+UNIQUE\s*;",
    re.IGNORECASE,
)


def apply_constraints(
    driver: Driver, constraints_file: Path = DEFAULT_CONSTRAINTS_FILE
) -> None:
    """Apply one semicolon-terminated uniqueness constraint per line."""
    statements: list[str] = []
    expected: set[tuple[str, str]] = set()
    for line_number, line in enumerate(
        constraints_file.read_text(encoding="utf-8").splitlines(), start=1
    ):
        statement = line.strip()
        if not statement:
            continue
        match = _CONSTRAINT.fullmatch(statement)
        if match is None:
            raise ValueError(f"Invalid constraint on line {line_number}.")
        statements.append(statement.removesuffix(";"))
        expected.add((match.group(2), match.group(3)))
    if not statements:
        raise ValueError("The constraints file is empty.")

    with driver.session() as session:
        for statement in statements:
            session.run(statement).consume()
        rows = session.run(
            "SHOW CONSTRAINTS YIELD type, entityType, labelsOrTypes, properties "
            "RETURN type, entityType, labelsOrTypes, properties"
        )
        actual = {
            (row["labelsOrTypes"][0], row["properties"][0])
            for row in rows
            if row["type"] == "UNIQUENESS"
            and row["entityType"] == "NODE"
            and len(row["labelsOrTypes"]) == 1
            and len(row["properties"]) == 1
        }
    missing = expected - actual
    if missing:
        details = ", ".join(
            f"{label}.{property_name}" for label, property_name in sorted(missing)
        )
        raise RuntimeError(f"Constraints were not applied: {details}.")


def main() -> None:
    """Apply constraints using the Neo4j credentials from the environment."""
    values = {}
    for name in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"):
        value = os.environ.get(name)
        if value is None or not value.strip():
            raise ValueError(f"{name} must be set.")
        values[name] = value
    with GraphDatabase.driver(
        values["NEO4J_URI"], auth=(values["NEO4J_USER"], values["NEO4J_PASSWORD"])
    ) as driver:
        apply_constraints(driver)


if __name__ == "__main__":
    main()
