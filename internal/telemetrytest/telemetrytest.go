package telemetrytest

import (
	"context"
	"testing"
	"time"

	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/sdk/trace/tracetest"
	"go.opentelemetry.io/otel/trace"
)

func SetupTracer(t *testing.T) (*tracetest.SpanRecorder, trace.Tracer) {
	t.Helper()

	recorder := tracetest.NewSpanRecorder()
	provider := sdktrace.NewTracerProvider(sdktrace.WithSpanProcessor(recorder))

	t.Cleanup(func() {
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()

		if err := provider.Shutdown(shutdownCtx); err != nil {
			t.Logf("failed to shutdown test tracer provider: %v", err)
		}
	})

	tracer := provider.Tracer("test-tracer")

	return recorder, tracer
}
