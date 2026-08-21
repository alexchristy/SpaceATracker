package telemetry

import (
	"context"
	"fmt"

	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/metric"
	"go.opentelemetry.io/otel/trace"
)

// OTelAdapter orchestrates data collection and publishing to OpenTelemetry providers.
type OTelAdapter struct {
	itemCounter       metric.Int64Counter
	durationHistogram metric.Float64Histogram
	tracer            trace.Tracer
}

// NewOTelAdapter constructs a OpenTelemetry adapter with required dependencies.
func NewOTelAdapter(meter metric.Meter, tracer trace.Tracer) (*OTelAdapter, error) {
	// Initialize metrics instruments
	item, err := meter.Int64Counter("items_processed_total")
	if err != nil {
		return nil, fmt.Errorf("create items_processed_total metric counter: %w", err)
	}

	duration, err := meter.Float64Histogram("operation_duration_seconds")
	if err != nil {
		return nil, fmt.Errorf("create operation_duration_seconds metric histogram: %w", err)
	}

	return &OTelAdapter{
		itemCounter:       item,
		durationHistogram: duration,
		tracer:            tracer,
	}, nil
}

// RecordItemCount records labeled integer counts.
func (o *OTelAdapter) RecordItemCount(ctx context.Context, opType, itemType string, count int64) {
	attrs := metric.WithAttributes(
		attribute.String("operation_type", opType),
		attribute.String("item_type", itemType),
	)
	o.itemCounter.Add(ctx, count, attrs)
}

// StartSpan starts a telemetry span inside the function where it's called and returns anupdated context and completion hook.
//
// The returned completion hook MUST be deferred and REQUIRES the use of the caller's named return error (e.g., `defer(done(&err))`).
// Passing nil or an un-named error will prevent error capture.
func (o *OTelAdapter) StartSpan(ctx context.Context, name string) (spanCtx context.Context, done func(*error)) {
	spanCtx, span := o.tracer.Start(ctx, name)

	// Return closure that handles status evaluation and cleanup
	done = func(errPtr *error) {
		if errPtr != nil && *errPtr != nil {
			span.RecordError(*errPtr)
			span.SetStatus(codes.Error, (*errPtr).Error())
		}
		span.End()
	}

	return spanCtx, done
}
