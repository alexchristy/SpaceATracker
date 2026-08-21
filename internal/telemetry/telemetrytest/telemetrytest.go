// Package telemetrytest provides testing mocks for telemetry adapters.
package telemetrytest

import (
	"context"
	"sync"
)

// SpyEngine records telemetry adapter activity and interactions.
type SpyEngine struct {
	mu sync.Mutex

	// RecordItemCount
	RecordItemCountInvocations int

	// StartSpan
	StartSpanInvocations int
}

// NewSpyEngine constructs a new telemetry adapater mock.
func NewSpyEngine() *SpyEngine {
	return &SpyEngine{
		RecordItemCountInvocations: 0,
		StartSpanInvocations:       0,
	}
}

// RecordItemCount records it's own invocation count.
func (s *SpyEngine) RecordItemCount(ctx context.Context, opType, itemType string, count int64) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.RecordItemCountInvocations++
}

// StartSpan records it's own invocation count.
func (s *SpyEngine) StartSpan(ctx context.Context, name string) (spanCtx context.Context, done func(*error)) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.StartSpanInvocations++

	return ctx, func(_ *error) {}
}
