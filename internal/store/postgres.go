package store

import (
	"context"
	"fmt"

	"github.com/jackc/pgx/v5/pgxpool"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/trace"

	"github.com/alexchristy/SpaceATracker/internal/store/dbgen"
)

// PostgresAdapterName is the canonical name used for logging and telemetry spans.
const PostgresAdapterName = "postgres"

// NewPostgresPool creates a connection pool for query execution.
func NewPostgresPool(ctx context.Context, connStr string) (*pgxpool.Pool, error) {
	pool, err := pgxpool.New(ctx, connStr)
	if err != nil {
		return nil, fmt.Errorf("database connection pool creation: %w", err)
	}

	return pool, nil
}

// PostgresAdapter orchestrates queries and interactions with the database layer.
type PostgresAdapter struct {
	db      *pgxpool.Pool
	queries *dbgen.Queries
	tracer  trace.Tracer
}

// NewPostgresAdapter constructs a postgres adapter with required dependencies.
func NewPostgresAdapter(pool *pgxpool.Pool, tracer trace.Tracer) *PostgresAdapter {
	return &PostgresAdapter{
		db:      pool,
		queries: dbgen.New(pool),
		tracer:  tracer,
	}
}

// SaveTerminalURLs stores discovered Space-A terminal URLs in the postgres database.
//
// URLs are stored in the `discovered_terminals` table.
func (p *PostgresAdapter) SaveTerminalURLs(ctx context.Context, terminalURLs []string) (err error) {
	// Start telemetry trace
	ctx, span := p.tracer.Start(ctx, PostgresAdapterName+".SaveTerminalURLs")
	defer func() {
		if err != nil {
			span.RecordError(err)
			span.SetStatus(codes.Error, err.Error())
		}
		span.End()
	}()

	batch := p.queries.UpsertTerminals(ctx, terminalURLs)
	defer func() {
		_ = batch.Close()
	}()

	var batchErr error
	batch.Exec(func(i int, err error) {
		if err != nil && batchErr == nil {
			batchErr = fmt.Errorf("upsert terminal '%q': %w", terminalURLs[i], err)
		}
	})

	if batchErr != nil {
		return fmt.Errorf("batch update terminal URLs: %w", batchErr)
	}

	if err := batch.Close(); err != nil {
		return fmt.Errorf("close batch flush: %w", err)
	}

	return nil
}
