// Package telemetry contains adapters for different telemetry providers.
package telemetry

import (
	"context"
)

// Engine defines the contract for telemetry adapters.
type Engine interface {
	RecordItemCount(ctx context.Context, opType, itemType string, count int64)

	// StartSpan starts a telemetry span inside the function where it's called and returns anupdated context and completion hook.
	//
	// The returned completion hook MUST be deferred and REQUIRES the use of the caller's named return error (e.g., `defer done(&err)`).
	// Passing nil or an un-named error will prevent error capture.
	StartSpan(ctx context.Context, name string) (context.Context, func(*error))
}
