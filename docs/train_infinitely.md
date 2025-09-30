# Operating Infinite Training Loops Safely

Running an "infinite" training job is rarely about looping forever. It is about
continuously improving an agent while keeping human operators, infrastructure,
and data safe. This playbook distills the practices we rely on when orchestrating
long-lived AutoGPT runs.

## Establish a Safety Envelope

| Guardrail | Why it matters | Practical implementation |
|-----------|----------------|---------------------------|
| **Termination budgets** | Prevents forgotten jobs from racking up cost. | Require both `max_steps` and `max_seconds` to be configurable, and enforce them inside the loop. |
| **Manual stop switch** | Gives operators an instant kill switch. | Poll for a `stop` file or remote flag every iteration. |
| **Signal handling** | Allows graceful shutdown from Kubernetes, systemd, etc. | Install SIGINT/SIGTERM handlers that set a shared `stop_requested` flag. |

Document the chosen limits next to the run configuration so future you knows why
the loop exits.

## Persist State Frequently

Infinite training is only viable when you can resume. At minimum, checkpoint:

- The model or policy parameters.
- Optimizer state (or other learnable schedulers).
- Key metrics from the latest step.
- Random generator seeds.

Store checkpoints atomically by writing to a temporary path and renaming once the
write succeeds. When multiple workers collaborate, guard with a distributed lock
or dedicated checkpointing service.

## Make Progress Observable

Operators need confidence that the loop is healthy. Combine layered telemetry:

- **Structured logs** emitted at a steady cadence with metrics like loss,
  tokens per second, and budget consumption.
- **Periodic heartbeats** to a monitoring stack (for example, Prometheus,
  Grafana, or OpenTelemetry). Include the last-success timestamp so alerts can
  fire on silence.
- **Artifact trails** such as JSON summaries or parquet files that analysts can
  query offline.

## Layer Recovery Hooks

Even with careful coding, long jobs encounter network glitches, bad batches, or
operator interrupts. Wrap the training loop in a supervisor that can:

- Retry transient failures with exponential backoff.
- Escalate to a human after a threshold number of retries.
- Trigger self-diagnostics (for example, run health checks and verify data integrity).

An orchestration entrypoint might resemble the following:

```python
while True:
    try:
        run_training_epoch()
    except TransientError as exc:
        logger.warning("Transient failure: %s", exc)
        if not backoff_retry():
            raise
    except Exception:
        alert_ops()
        raise
    if budget_exhausted() or manual_stop_requested():
        break
```

## Treat Data Streams as First-Class Citizens

Infinite loops often consume unbounded data. Use queues or streaming systems
that support back-pressure and replay, and record offsets so restarts do not
lose progress. Validate payloads defensively to avoid poisoning the model with
malformed batches.

## Automate Governance

An infinite run should still respect regulatory and organizational boundaries.
Automate the safeguards that auditors will ask about:

- Budget accounting per team or feature flag.
- Access control to production APIs or private datasets.
- Audit logs that explain *why* the agent made significant decisions.

## Practice Controlled Drills

Before letting a loop run for days, simulate failures in staging:

- Kill the process and ensure it resumes from the latest checkpoint.
- Revoke network access temporarily to validate retry logic.
- Inject corrupted batches and confirm the data validation rejects them.

Document the results. The best incident response is preparation.

## Use the Helper Script

The repository ships with `docs/train_infinitely.py`, a sandboxed trainer that
demonstrates the controls described above. It can be invoked either with
`python -m docs.train_infinitely` or by executing the file directly. At least one
of `--max-steps` or `--max-seconds` must be set, and checkpoints are persisted at
the cadence specified by `--checkpoint-interval`.

Key command-line features include:

- `--stop-file` monitors for a sentinel file so operators can request a graceful
  shutdown without sending a signal.
- `--heartbeat-seconds` drives periodic debug logs that confirm the run is still
  alive.
- `--seed` ensures reproducible metric sequences while exercising the script.

The helper is intentionally lightweight; replace `simulate_training_step` with
your own model update routine when adapting these patterns to production.

---

Infinite training can be a powerful way to grow an agent's capabilities, but the
practice succeeds only when wrapped in robust guardrails. Revisit this playbook
regularly and treat every long-running job as production-critical.
