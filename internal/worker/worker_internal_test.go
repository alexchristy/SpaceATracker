package worker

import (
	"context"
	"errors"
	"log/slog"
	"sync/atomic"
	"testing"
	"time"
)

func TestTimedWorker_Run_ErrorThreshold(t *testing.T) {
	t.Parallel()

	var executions int
	task := func(taskCtx context.Context) error {
		executions++

		// No error on startup to trigger consecutive error counter
		if executions > 1 {
			return errors.New("mock error")
		}

		return nil
	}

	discardLogger := slog.New(slog.DiscardHandler)
	cfg := TimedWorkerConfig{
		Logger:   discardLogger,
		Interval: 1 * time.Millisecond,
		Task:     task,
	}
	worker := NewTimedWorker(cfg)

	done := make(chan struct{})
	go func() {
		defer close(done)
		worker.Run(t.Context())
	}()

	select {
	case <-done:
		// Worker exits cleanly
	case <-time.After(1 * time.Second):
		t.Fatal("timed worker failed to exit after consecutive errors")
	}

	// 1 startup run + 3 consecutive error runs
	if executions != 4 {
		t.Errorf("Run() executions = %d, want %d", executions, 4)
	}
}

func TestTimedWorker_Run_ErrorThresholdReset(t *testing.T) {
	t.Parallel()

	ctx, cancel := context.WithCancel(t.Context())
	defer cancel()

	var executions atomic.Int32
	task := func(taskCtx context.Context) error {
		executions.Add(1)

		// No error on startup to trigger consecutive error counter
		if executions.Load()%2 == 0 {
			return errors.New("mock error")
		}

		return nil
	}

	discardLogger := slog.New(slog.DiscardHandler)
	cfg := TimedWorkerConfig{
		Logger:   discardLogger,
		Interval: 1 * time.Millisecond,
		Task:     task,
	}
	worker := NewTimedWorker(cfg)

	done := make(chan struct{})
	go func() {
		defer close(done)
		worker.Run(ctx)
	}()

	select {
	case <-done:
		// Worker exits cleanly
	case <-time.After(10 * time.Millisecond):
		cancel()
	case <-time.After(1 * time.Second):
		t.Fatal("timed worker failed to exit after canceled context")
	}

	// If the consecutive error reset fails the function can execute a maximum of 4 times (1 on startup + 3 errors)
	if executions.Load() <= 5 {
		t.Errorf("Run() executions = %d, want >= %d", executions.Load(), 5)
	}
}

func TestTimedWorker_Run_CanceledContext(t *testing.T) {
	t.Parallel()

	ctx, cancel := context.WithCancel(t.Context())
	defer cancel()

	discardLogger := slog.New(slog.DiscardHandler)
	task := func(taskCtx context.Context) error {
		return nil
	}

	cfg := TimedWorkerConfig{
		Logger:   discardLogger,
		Interval: 1 * time.Millisecond,
		Task:     task,
	}
	worker := NewTimedWorker(cfg)

	done := make(chan struct{})
	go func() {
		defer close(done)
		worker.Run(ctx)
	}()

	select {
	case <-done:
		// Worker exits cleanly
	case <-time.After(1 * time.Millisecond):
		// Simulate externally canceled context
		cancel()
	case <-time.After(1 * time.Second):
		t.Fatal("timed worker failed to exit after context canceled")
	}
}

func TestTimedWorker_Run_StartupCanceledContext(t *testing.T) {
	t.Parallel()

	ctx, cancel := context.WithCancel(t.Context())
	cancel()

	discardLogger := slog.New(slog.DiscardHandler)
	var executions int
	task := func(taskCtx context.Context) error {
		executions++
		return nil
	}

	cfg := TimedWorkerConfig{
		Logger:   discardLogger,
		Interval: 1 * time.Millisecond,
		Task:     task,
	}
	worker := NewTimedWorker(cfg)

	worker.Run(ctx)

	if executions > 0 {
		t.Fatal("timed worker did not abort before startup with canceled context")
	}
}

func TestTimedWorker_Run_StartupError(t *testing.T) {
	t.Parallel()

	discardLogger := slog.New(slog.DiscardHandler)
	var executions int
	task := func(taskCtx context.Context) error {
		executions++
		return errors.New("mock error")
	}

	cfg := TimedWorkerConfig{
		Logger:   discardLogger,
		Interval: 1 * time.Millisecond,
		Task:     task,
	}
	worker := NewTimedWorker(cfg)

	worker.Run(t.Context())

	if executions != 1 {
		t.Fatalf("timed worker with start up error executed %d times, want %d", executions, 1)
	}
}
