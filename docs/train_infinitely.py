"""Utility script for running an open-ended training loop with safety rails.

This module exposes a CLI entry point that keeps running training steps until a
configurable shutdown condition is met (max steps, max duration, or OS signal).
It demonstrates best practices for long-running loops including:

* Structured logging and metrics sampling
* Periodic checkpoint persistence
* Deterministic PRNG seeding for reproducibility
* Graceful shutdown on SIGINT/SIGTERM
* Heartbeat logging to aid observability

The simulated training step simply perturbs a floating-point "loss" value so the
script can be executed without heavyweight dependencies.
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import signal
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

LOGGER = logging.getLogger(__name__)


@dataclass
class TrainingState:
    """Serializable training state stored in checkpoints."""

    step: int
    loss: float
    best_loss: float


@dataclass
class TrainingConfig:
    """User-configurable runtime parameters."""

    checkpoint_dir: Path
    checkpoint_interval: int
    metrics_interval: int
    max_seconds: Optional[float]
    max_steps: Optional[int]
    seed: Optional[int]
    heartbeat_seconds: float = 30.0
    stop_file: Optional[Path] = None


class GracefulKiller:
    """Signal handler that defers shutdown until the current iteration ends."""

    def __init__(self) -> None:
        self._received_signal: Optional[int] = None
        self._original_handlers: dict[int, signal.Handlers] = {}

    def install(self) -> None:
        for sig in (signal.SIGINT, signal.SIGTERM):
            self._original_handlers[sig] = signal.getsignal(sig)
            signal.signal(sig, self._handle_signal)

    def restore(self) -> None:
        for sig, handler in self._original_handlers.items():
            signal.signal(sig, handler)

    def _handle_signal(self, signum: int, frame: Optional[object]) -> None:  # noqa: ARG002
        if self._received_signal is None:
            LOGGER.warning("Received signal %s – will stop after current step.", signum)
            self._received_signal = signum
        else:
            LOGGER.error(
                "Received signal %s while already shutting down. Exiting immediately.",
                signum,
            )
            self.restore()
            sys.exit(1)

    @property
    def received_signal(self) -> Optional[int]:
        return self._received_signal


def parse_args(argv: Optional[list[str]] = None) -> TrainingConfig:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        required=True,
        help="Directory to write checkpoint files into.",
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=10,
        help="Steps between checkpoint writes.",
    )
    parser.add_argument(
        "--metrics-interval",
        type=int,
        default=5,
        help="Steps between metrics logging.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Optional maximum number of steps to execute.",
    )
    parser.add_argument(
        "--max-seconds",
        type=float,
        default=None,
        help="Optional wall-clock limit for the run.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for deterministic behaviour.",
    )
    parser.add_argument(
        "--heartbeat-seconds",
        type=float,
        default=30.0,
        help="Interval for periodic heartbeat logs during long runs.",
    )
    parser.add_argument(
        "--stop-file",
        type=Path,
        default=None,
        help="Optional file path that, when present, requests a graceful stop.",
    )

    args = parser.parse_args(argv)

    if args.checkpoint_interval <= 0:
        parser.error("--checkpoint-interval must be positive")
    if args.metrics_interval <= 0:
        parser.error("--metrics-interval must be positive")
    if args.max_steps is not None and args.max_steps <= 0:
        parser.error("--max-steps must be positive when provided")
    if args.max_seconds is not None and args.max_seconds <= 0:
        parser.error("--max-seconds must be positive when provided")
    if args.heartbeat_seconds <= 0:
        parser.error("--heartbeat-seconds must be positive")
    if args.stop_file is not None and args.stop_file.is_dir():
        parser.error("--stop-file must be a file path, not a directory")
    if args.max_steps is None and args.max_seconds is None:
        parser.error("Provide at least one of --max-steps or --max-seconds")

    return TrainingConfig(
        checkpoint_dir=args.checkpoint_dir,
        checkpoint_interval=args.checkpoint_interval,
        metrics_interval=args.metrics_interval,
        max_seconds=args.max_seconds,
        max_steps=args.max_steps,
        seed=args.seed,
        heartbeat_seconds=args.heartbeat_seconds,
        stop_file=args.stop_file,
    )


def load_checkpoint(checkpoint_dir: Path) -> Optional[TrainingState]:
    latest = checkpoint_dir / "latest.json"
    if not latest.exists():
        return None
    try:
        with latest.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
            return TrainingState(**payload)
    except Exception as exc:  # noqa: BLE001 - best effort
        LOGGER.error("Failed to load checkpoint %s: %s", latest, exc)
        return None


def save_checkpoint(state: TrainingState, checkpoint_dir: Path) -> None:
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = checkpoint_dir / f"step-{state.step}.json.tmp"
    final_path = checkpoint_dir / f"step-{state.step}.json"
    latest_path = checkpoint_dir / "latest.json"

    data = asdict(state)
    with tmp_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    tmp_path.replace(final_path)
    latest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Checkpoint saved at step %s", state.step)


def simulate_training_step(state: TrainingState) -> TrainingState:
    noise = random.gauss(mu=0.0, sigma=0.05)
    new_loss = max(state.loss + noise, 0.0)
    best_loss = min(state.best_loss, new_loss)
    return TrainingState(step=state.step + 1, loss=new_loss, best_loss=best_loss)


def maybe_log_metrics(state: TrainingState) -> None:
    LOGGER.info(
        "Metrics | step=%d loss=%.4f best_loss=%.4f",
        state.step,
        state.loss,
        state.best_loss,
    )


def run_training(config: TrainingConfig) -> TrainingState:
    if config.seed is not None:
        random.seed(config.seed)
        LOGGER.info("Seeded RNG with %s", config.seed)

    state = load_checkpoint(config.checkpoint_dir)
    if state is None:
        state = TrainingState(step=0, loss=1.0, best_loss=1.0)
        LOGGER.info("Starting fresh training run")
    else:
        LOGGER.info("Resuming from checkpoint at step %d", state.step)

    killer = GracefulKiller()
    killer.install()
    start_time = time.monotonic()
    last_heartbeat = start_time

    try:
        while True:
            now = time.monotonic()
            elapsed = now - start_time

            if config.max_seconds is not None and elapsed >= config.max_seconds:
                LOGGER.info("Reached max_seconds=%.2f, stopping.", config.max_seconds)
                break
            if config.max_steps is not None and state.step >= config.max_steps:
                LOGGER.info("Reached max_steps=%d, stopping.", config.max_steps)
                break
            if killer.received_signal is not None:
                LOGGER.info("Stopping due to received signal %s", killer.received_signal)
                break
            if config.stop_file is not None and config.stop_file.exists():
                LOGGER.info("Detected stop file at %s, shutting down.", config.stop_file)
                break

            state = simulate_training_step(state)

            if state.step % config.metrics_interval == 0:
                maybe_log_metrics(state)
            if state.step % config.checkpoint_interval == 0:
                save_checkpoint(state, config.checkpoint_dir)

            if now - last_heartbeat >= config.heartbeat_seconds:
                LOGGER.debug("Heartbeat: elapsed=%.1fs step=%d", elapsed, state.step)
                last_heartbeat = now

            time.sleep(0.1)
    finally:
        killer.restore()

    save_checkpoint(state, config.checkpoint_dir)
    LOGGER.info("Training stopped at step %d", state.step)
    return state


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def main(argv: Optional[list[str]] = None) -> int:
    configure_logging()
    config = parse_args(argv)
    try:
        run_training(config)
    except Exception:  # noqa: BLE001
        LOGGER.exception("Training run failed")
        return 1
    return 0


if __name__ == "main":
    raise SystemExit("Use `python -m docs.train_infinitely` to run this module.")

if __name__ == "__main__":
    raise SystemExit(main())
