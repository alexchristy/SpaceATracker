// The worker starts workers for the AMC scraping processing pipeline.
package main

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"go.opentelemetry.io/otel"

	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/trace"

	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"

	"github.com/alexchristy/SpaceATracker/internal/client"
	"github.com/alexchristy/SpaceATracker/internal/config"
	"github.com/alexchristy/SpaceATracker/internal/discovery"
	"github.com/alexchristy/SpaceATracker/internal/store"
	"github.com/alexchristy/SpaceATracker/internal/worker"
)

func main() {
	logger := setupLogger()
	logger.Info("logger configured")

	if err := run(logger); err != nil {
		logger.Error("fatal worker execution error", slog.Any("error", err))
		os.Exit(1)
	}
}

func run(logger *slog.Logger) error {
	// Env
	cfg, err := loadEnv()
	if err != nil {
		return fmt.Errorf("configure environment: %w", err)
	}
	logger.Info("loaded config",
		slog.String("terminalIndexUrl", cfg.TerminalIndexURL),
		slog.Duration("discoveryInterval", cfg.DiscoveryInterval),
	)

	// Initialize context
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	// Configure telemetry
	tracer, shutdownTelemetry, err := setupOpenTelemetry(ctx)
	if err != nil {
		return fmt.Errorf("configure telemetry: %w", err)
	}
	defer func() {
		shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 15*time.Second)
		defer shutdownCancel()
		if err = shutdownTelemetry(shutdownCtx); err != nil {
			logger.Error("failed to shutdown telemetry", slog.Any("error", err))
		}
	}()

	// Connect to database
	pool, err := store.NewPostgresPool(ctx, cfg.DatabaseURI)
	if err != nil {
		return fmt.Errorf("initialize database: %w", err)
	}
	db := store.NewPostgresAdapter(pool, tracer)

	// Connect to scraper API
	scraperClient := client.NewZyte(client.ZyteApiURL, cfg.ScraperApiKey, tracer)

	// Initialize wait group
	var wg sync.WaitGroup

	// Service: Terminal Disovery
	discoveryLogger := logger.With(slog.String("worker", "discovery"))
	discoverySvc := discovery.NewService(
		db,
		scraperClient,
		tracer,
		discoveryLogger,
	)
	discoveryWorkerCfg := worker.TimedWorkerConfig{
		Logger:   discoveryLogger,
		Interval: cfg.DiscoveryInterval,
		Task: func(workerCtx context.Context) error {
			return discoverySvc.Execute(workerCtx, cfg.TerminalIndexURL)
		},
	}

	discoveryWorker := worker.NewTimedWorker(discoveryWorkerCfg)
	wg.Add(1)
	go func() {
		defer wg.Done()
		discoveryWorker.Run(ctx)
	}()

	// Block until canceled by OS
	<-ctx.Done()
	logger.Info("shutdown signal received, waiting for workers to finish...")

	// Shutdown timeout
	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer shutdownCancel()

	done := make(chan struct{})
	go func() {
		wg.Wait()
		close(done)
	}()

	select {
	case <-done:
		logger.InfoContext(shutdownCtx, "all workers shut down cleanly")
	case <-shutdownCtx.Done():
		logger.ErrorContext(shutdownCtx, "shutdown timeout exceeded, forcing exit")
		return nil
	}

	return nil
}

func setupLogger() *slog.Logger {
	// Initialize logging
	opts := &slog.HandlerOptions{
		Level: slog.LevelInfo,
	}
	logger := slog.New(slog.NewJSONHandler(os.Stdout, opts))
	slog.SetDefault(logger)
	return logger
}

func loadEnv() (config.Config, error) {
	// Load config
	cfg, err := config.Load()
	if err != nil {
		return config.Config{}, fmt.Errorf("configuration failure: %w", err)
	}

	return cfg, nil
}

func setupOpenTelemetry(ctx context.Context) (trace.Tracer, func(context.Context) error, error) {
	// Env vars
	res, err := resource.New(
		ctx,
		resource.WithFromEnv(),
		resource.WithTelemetrySDK(),
	)
	if err != nil {
		return nil, nil, fmt.Errorf("create telemetry resource: %w", err)
	}

	// Configure traces
	traceExporter, err := otlptracehttp.New(ctx)
	if err != nil {
		return nil, nil, fmt.Errorf("create telemetry trace exporter: %w", err)
	}
	tracerProvider := sdktrace.NewTracerProvider(
		sdktrace.WithResource(res),
		sdktrace.WithBatcher(traceExporter),
	)
	otel.SetTracerProvider(tracerProvider)

	// Extract instrument
	tracer := tracerProvider.Tracer("github.com/alexchristy/SpaceATracker")

	shutdown := func(shutdownCtx context.Context) error {
		if err := tracerProvider.Shutdown(shutdownCtx); err != nil {
			return fmt.Errorf("shutdown telemetry provider: %w", err)
		}
		return nil
	}

	return tracer, shutdown, nil
}
