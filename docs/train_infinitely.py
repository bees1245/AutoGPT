"""Utility script that demonstrates how to run an "infinite" training loop safely.

The loop keeps iterating over a never-ending data stream, but it respects
operational guard rails such as:

* graceful shutdown on SIGINT/SIGTERM
* resource budgets (max steps / max wall clock time)
* filesystem stop signals
* time-based checkpoints for recovery
* periodic metric logging

Run it with ``python docs/train_infinitely.py --help`` for CLI options.
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterator, Optional


LOGGER = logging.getLogger("infinite-training")


@dataclass
class TrainingConfig:
    """Configuration flags that govern the training loop."""

    checkpoint_interval: timedelta
    checkpoint_dir: Path
    max_steps: Optional[int] = None
    max_seconds: Optional[float] = None
    stop_file: Optional[Path] = None
    metrics_interval: int = 25


@dataclass
class TrainingState:
    """Mutable state that persists across training steps."""

    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_checkpoint: datetime = field(default_factory=lambda: datetime.now(UTC))
    step: int = 0
    loss: float = 10.0


class SyntheticDataset:
    """Generates an endless stream of pseudo-random mini-batches."""

    def __iter__(self) -> Iterator[list[float]]:
        while True:
            batch_size = random.randint(8, 32)
            yield [random.random() for _ in range(batch_size)]


class Trainer:
    """Toy trainer that simulates a monotonically improving loss curve."""

    def __init__(self, state: TrainingState) -> None:
        self._state = state

    def train_step(self, batch: list[float]) -> dict[str, float]:
        # Pretend the model improves slightly each step with some noise.
        improvement = 0.04 + random.random() * 0.02
        noise = random.random() * 0.01
        self._state.loss = max(self._state.loss * (1 - improvement) + noise, 0.0001)
        time.sleep(0.02)  # Simulate work being done.
        return {"loss": self._state.loss}

    def save_checkpoint(self, path: Path) -> None:
        path.write_text(
            json.dumps(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "step": self._state.step,
                    "loss": self._state.loss,
                },
                indent=2,
            )
        )


class InfiniteTrainingRun:
    def __init__(self, config: TrainingConfig) -> None:
        self.config = config
        self.state = TrainingState()
        self.dataset = SyntheticDataset()
        self.trainer = Trainer(self.state)
        self._stop_requested = False

    # -- signal handling -------------------------------------------------
    def install_signal_handlers(self) -> None:
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._handle_stop_signal)

    def _handle_stop_signal(self, signum, _frame) -> None:  # type: ignore[override]
        LOGGER.warning("Received signal %s, requesting graceful stop", signum)
        self._stop_requested = True

    # -- runtime guards --------------------------------------------------
    def _stop_reason(self) -> Optional[str]:
        if self._stop_requested:
            return "stop requested via signal"
        if self.config.max_steps is not None and self.state.step >= self.config.max_steps:
            return "max steps reached"
        if self.config.max_seconds is not None:
            elapsed = (datetime.now(UTC) - self.state.start_time).total_seconds()
            if elapsed >= self.config.max_seconds:
                return "max runtime reached"
        if self.config.stop_file and self.config.stop_file.exists():
            return f"stop file detected at {self.config.stop_file}"
        return None

    def _maybe_checkpoint(self) -> None:
        elapsed = datetime.now(UTC) - self.state.last_checkpoint
        if elapsed < self.config.checkpoint_interval:
            return

        self.config.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = self.config.checkpoint_dir / f"step-{self.state.step:08d}.json"
        self.trainer.save_checkpoint(checkpoint_path)
        self.state.last_checkpoint = datetime.now(UTC)
        LOGGER.info("Saved checkpoint -> %s", checkpoint_path)

    # -- main loop -------------------------------------------------------
    def run(self) -> None:
        self.install_signal_handlers()
        for batch in self.dataset:
            self.state.step += 1
            metrics = self.trainer.train_step(batch)

            if self.state.step % self.config.metrics_interval == 0:
                LOGGER.info(
                    "step=%s loss=%.4f elapsed=%.1fs",
                    self.state.step,
                    metrics["loss"],
                    (datetime.now(UTC) - self.state.start_time).total_seconds(),
                )

            self._maybe_checkpoint()

            reason = self._stop_reason()
            if reason:
                LOGGER.info("Stopping training: %s", reason)
                break


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=Path("./checkpoints"),
        help="Directory where checkpoints will be written.",
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=300,
        metavar="SECONDS",
        help="Seconds between checkpoints (default: 300).",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        help="Optional cap on training steps before exiting.",
    )
    parser.add_argument(
        "--max-seconds",
        type=float,
        help="Optional cap on wall clock runtime before exiting.",
    )
    parser.add_argument(
        "--stop-file",
        type=Path,
        help="If this file exists, the loop stops at the next opportunity.",
    )
    parser.add_argument(
        "--metrics-interval",
        type=int,
        default=25,
        help="Log metrics every N steps (default: 25).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Seed for the pseudo-random number generator to make runs reproducible.",
    )
    return parser.parse_args(argv)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.seed is not None:
        random.seed(args.seed)

    configure_logging()
    config = TrainingConfig(
        checkpoint_interval=timedelta(seconds=args.checkpoint_interval),
        checkpoint_dir=args.checkpoint_dir,
        max_steps=args.max_steps,
        max_seconds=args.max_seconds,
        stop_file=args.stop_file,
        metrics_interval=max(1, args.metrics_interval),
    )

    run = InfiniteTrainingRun(config)
    try:
        run.run()
    except Exception:
        LOGGER.exception("Training loop terminated due to an unexpected error")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
