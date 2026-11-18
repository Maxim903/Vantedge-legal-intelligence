"""Exercise deployment arguments without contacting Google Cloud."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/deploy_jobs.sh"


@pytest.fixture
def deployment(tmp_path):
    gcloud = tmp_path / "gcloud"
    gcloud.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"$*\" >> \"$GCLOUD_LOG\"\n"
        "if [ \"$1 $2 $3\" = 'scheduler jobs list' ]; then\n"
        "  [ \"${FAIL_LIST:-0}\" = 0 ] || exit 9\n"
        "  printf '%s\\n' \"${EXISTING_JOBS:-}\"\n"
        "fi\n"
    )
    gcloud.chmod(0o755)
    log = tmp_path / "calls"
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "GCLOUD_LOG": str(log),
        "PROJECT_ID": "test-project",
        "IMAGE": "registry.example/image:123",
        "JOB_SERVICE_ACCOUNT": "job@test-project.iam.gserviceaccount.com",
        "SCHEDULER_SERVICE_ACCOUNT": "scheduler@test-project.iam.gserviceaccount.com",
        "GCS_BUCKET_RAW": "test-raw",
        "CORPUS_BUCKET": "test-corpus",
        "CORPUS_OBJECT": "legi/archive.tar.gz",
        "EXTRACTION_MAX_COST": "10",
        "EXTRACTION_COST_PER_CALL": "0.001",
        "VOLUMES_MAX_COST": "20",
        "VOLUMES_COST_PER_CALL": "0.002",
        "LLM_SECRET": "llm",
        "DATAFORSEO_LOGIN_SECRET": "login",
        "DATAFORSEO_PASSWORD_SECRET": "password",
        "NEO4J_URI_SECRET": "uri",
        "NEO4J_USER_SECRET": "user",
        "NEO4J_PASSWORD_SECRET": "neo-password",
    }
    return env, log


def run_deploy(env):
    return subprocess.run(  # noqa: S603
        ["/bin/bash", str(SCRIPT)], env=env, text=True, capture_output=True, check=False
    )


def test_deploys_six_jobs_and_creates_oauth_schedules(deployment):
    env, log = deployment
    result = run_deploy(env)
    assert result.returncode == 0, result.stderr
    calls = log.read_text().splitlines()
    jobs = [line for line in calls if line.startswith("run jobs deploy ")]
    assert len(jobs) == 6
    assert all("--max-retries=1" in line and "--tasks=1" in line for line in jobs)
    assert "bucket=test-corpus,readonly=true" in jobs[0]
    assert "/mnt/corpus/legi/archive.tar.gz" in jobs[0]
    assert "--set-secrets=/secrets/llm/key=llm:latest" in jobs[1]
    assert "/secrets/dataforseo/login=login:latest" in jobs[2]
    assert "/secrets/neo4j/password=neo-password:latest" in jobs[5]
    schedules = [
        line for line in calls if line.startswith("scheduler jobs create http ")
    ]
    assert len(schedules) == 2
    assert "--schedule=0 3 1 * *" in schedules[0]
    assert "--schedule=0 4 * * 1" in schedules[1]
    assert all("--oauth-service-account-email=" in line for line in schedules)
    assert all("--max-retry-attempts=0" in line for line in schedules)
    assert len([line for line in calls if "add-iam-policy-binding" in line]) == 2


def test_existing_schedules_are_updated_and_list_errors_stop(deployment):
    env, log = deployment
    env["EXISTING_JOBS"] = (
        "projects/test-project/locations/europe-west9/jobs/vil-collect-volumes-monthly\n"
        "vil-sync-graph-weekly"
    )
    result = run_deploy(env)
    assert result.returncode == 0, result.stderr
    assert log.read_text().count("scheduler jobs update http ") == 2
    log.unlink()
    env["FAIL_LIST"] = "1"
    result = run_deploy(env)
    assert result.returncode != 0
    assert "scheduler jobs create" not in log.read_text()
    assert "scheduler jobs update" not in log.read_text()


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("CORPUS_OBJECT", "../secret"),
        ("LLM_SECRET", "bad,secret"),
        ("VOLUMES_COST_PER_CALL", "0"),
    ],
)
def test_invalid_configuration_fails_before_deployment(deployment, name, value):
    env, log = deployment
    env[name] = value
    result = run_deploy(env)
    assert result.returncode != 0
    assert result.stderr
    assert not log.exists()


@pytest.mark.parametrize(
    ("job", "executable", "expected"),
    [
        ("dbt", "dbt", "build --project-dir /app/dbt --profiles-dir /app/dbt"),
        ("load-raw-market", "python", "-m vil_pipeline.cli load-raw-market"),
    ],
)
def test_entrypoint_dispatches_jobs(tmp_path, job, executable, expected):
    binary = tmp_path / executable
    binary.write_text("#!/bin/sh\nprintf '%s\\n' \"$*\"\nexit 7\n")
    binary.chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}
    result = subprocess.run(  # noqa: S603
        ["/bin/sh", str(ROOT / "pipeline/job-entrypoint.sh"), job],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 7
    assert result.stdout.strip() == expected
