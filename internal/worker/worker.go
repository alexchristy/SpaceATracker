// Package worker implements task scheduling and execution queues.
package worker

import (
	"context"
	"log/slog"
	"time"
)

// RunnableFunc defines the contract for executable worker functions.
type RunnableFunc func(ctx context.Context) error

// TimedWorkerConfig defines the configuration and dependencies for a timed worker.
type TimedWorkerConfig struct {
	Logger   *slog.Logger
	Interval time.Duration
	Task     RunnableFunc
}

// TimedWorker executes function on a regular interval similar to a cron job.
type TimedWorker struct {
	cfg TimedWorkerConfig
}

// NewTimedWorker contructs a timed worker with required dependencies.
func NewTimedWorker(cfg TimedWorkerConfig) *TimedWorker {
	return &TimedWorker{
		cfg: cfg,
	}
}

// Run coordinates execution of the timed worker first on startup and then on the defined interval.
func (w *TimedWorker) Run(ctx context.Context) {
	ticker := time.NewTicker(w.cfg.Interval)
	defer ticker.Stop()

	consecutiveErrors := 0

	w.cfg.Logger.InfoContext(ctx, "starting timed worker execution loop")

	// Fail fast if context is dead before startup
	if err := ctx.Err(); err != nil {
		w.cfg.Logger.InfoContext(ctx, "timed worker aborted before startup", slog.Any("error", err))
		return
	}

	// Run it once on startup and exit early if there is an error
	if err := w.cfg.Task(ctx); err != nil {
		w.cfg.Logger.ErrorContext(ctx, "timed worker failed on startup", slog.Any("error", err))
		return
	}

	// Run on timer
	for {
		select {
		case <-ctx.Done():
			w.cfg.Logger.InfoContext(ctx, "timed worker shutting down cleanly")
			return

		case <-ticker.C:
			if err := w.cfg.Task(ctx); err != nil {
				w.cfg.Logger.WarnContext(ctx, "timed worker failed on timed execution", slog.Any("error", err))
				consecutiveErrors++
			} else {
				// Reset counter on a successful run
				consecutiveErrors = 0
			}

			if consecutiveErrors >= 3 {
				w.cfg.Logger.ErrorContext(ctx, "timed worker exceeded consecutive error threshold")
				return
			}
		}
	}
}
