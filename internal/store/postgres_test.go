//go:build integration

package store_test

import (
	"context"
	"errors"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/testcontainers/testcontainers-go"
	"github.com/testcontainers/testcontainers-go/modules/postgres"
	"github.com/testcontainers/testcontainers-go/network"
	"github.com/testcontainers/testcontainers-go/wait"

	"github.com/alexchristy/SpaceATracker/internal/store"
	"github.com/alexchristy/SpaceATracker/internal/telemetry/telemetrytest"
)

var (
	testPool    *pgxpool.Pool
	testConnStr string
)

func run(ctx context.Context, m *testing.M) (int, error) {
	// Create docker test network
	testNet, err := network.New(ctx)
	if err != nil {
		return 0, fmt.Errorf("create test network: %v", err)
	}
	defer func() {
		_ = testNet.Remove(ctx)
	}()

	// Create Postgres container
	const dbAlias = "postgres-db"
	pgContainer, err := postgres.Run(ctx,
		"postgres:18-alpine",
		postgres.WithDatabase("testdb"),
		postgres.WithUsername("testuser"),
		postgres.WithPassword("testpass"),
		network.WithNetwork([]string{dbAlias}, testNet),
		testcontainers.WithWaitStrategy(
			wait.ForLog("database system is ready to accept connections").
				WithOccurrence(2).
				WithStartupTimeout(30*time.Second),
		),
	)
	if err != nil {
		return 0, fmt.Errorf("start postgres container: %v", err)
	}
	defer func() {
		_ = pgContainer.Terminate(ctx)
	}()

	// Locate migrations
	migrationPath, err := filepath.Abs("../../db/migrations")
	if err != nil {
		return 0, fmt.Errorf("resolve migration path: %v", err)
	}

	migrateReq := testcontainers.ContainerRequest{
		Image:    "migrate/migrate",
		Networks: []string{testNet.Name},
		Files: []testcontainers.ContainerFile{
			{
				HostFilePath:      migrationPath,
				ContainerFilePath: "/migrations",
				FileMode:          0o644,
			},
		},
		Cmd: []string{
			"-path=/migrations",
			"-database=postgres://testuser:testpass@" + dbAlias + ":5432/testdb?sslmode=disable",
			"up",
		},
		WaitingFor: wait.ForExit().WithExitTimeout(30 * time.Second),
	}

	migrateContainer, err := testcontainers.GenericContainer(ctx,
		testcontainers.GenericContainerRequest{
			ContainerRequest: migrateReq,
			Started:          true,
		},
	)
	if err != nil {
		return 0, fmt.Errorf("run migration container: %v", err)
	}
	defer func() {
		_ = migrateContainer.Terminate(ctx)
	}()

	// Get connection string for dependencies
	testConnStr, err = pgContainer.ConnectionString(ctx, "sslmode=disable")
	if err != nil {
		return 0, fmt.Errorf("retrieve connection string: %v", err)
	}

	testPool, err = store.NewPostgresPool(ctx, testConnStr)
	if err != nil {
		return 0, fmt.Errorf("connect to database pool: %v", err)
	}
	defer testPool.Close()

	return m.Run(), nil
}

func TestMain(m *testing.M) {
	ctx := context.Background()
	exitCode, err := run(ctx, m)
	if err != nil {
		log.Printf("postgres test container setup failed: %v", err)
		os.Exit(1)
	}

	os.Exit(exitCode)
}

func setupTest(t *testing.T) *pgxpool.Pool {
	t.Helper()

	_, err := testPool.Exec(t.Context(), "TRUNCATE TABLE discovered_terminals RESTART IDENTITY CASCADE;")
	if err != nil {
		t.Fatalf("truncate test tables: %v", err)
	}

	return testPool
}

func TestPostgres_SaveTerminalURLs_Success(t *testing.T) {
	pool := setupTest(t)
	spy := telemetrytest.NewSpyEngine()
	adapter := store.NewPostgresAdapter(pool, spy)

	inputs := []string{"https://fake1.url", "https://fake2.url"}
	if err := adapter.SaveTerminalURLs(t.Context(), inputs); err != nil {
		t.Fatalf("SaveTerminalURLs(%q) unexpected error: %v", inputs, err)
	}

	var count int
	err := pool.QueryRow(t.Context(), "SELECT COUNT(*) FROM discovered_terminals;").Scan(&count)
	if err != nil {
		t.Fatalf("row count query failed: %v", err)
	}

	if got, want := count, len(inputs); got != want {
		t.Errorf("row count = %d, want %d", got, want)
	}

	// Ensure a telemetry span was recorded
	if spy.StartSpanInvocations != 1 {
		t.Errorf("SaveTerminalURLs(%q) started spans %d, want %d", inputs, spy.StartSpanInvocations, 1)
	}
}

func TestPostgres_NewPostgresPool_Error(t *testing.T) {
	t.Parallel()

	invalidURL := "invalid://url"
	_, err := store.NewPostgresPool(t.Context(), invalidURL)

	if err == nil {
		t.Fatalf("NewPostgresPool(%q) expected error, got nil", invalidURL)
	}
}

func TestPostgres_SaveTerminalURLs_ContextCanceled(t *testing.T) {
	pool := setupTest(t)
	spy := telemetrytest.NewSpyEngine()
	adapter := store.NewPostgresAdapter(pool, spy)

	ctx, cancel := context.WithCancel(t.Context())
	cancel()

	inputs := []string{"https://fake.url"}
	err := adapter.SaveTerminalURLs(ctx, inputs)
	if err == nil {
		t.Fatalf("SaveTerminalURLs(%q) expected error, got nil", inputs)
	}

	if !errors.Is(err, context.Canceled) {
		t.Errorf("SaveTerminalURLs(%q) error = %v, want %v", inputs, err, context.Canceled)
	}

	// Ensure that a telemetry span was recorded
	if spy.StartSpanInvocations != 1 {
		t.Errorf("SaveTerminalURLs(%q) started spans %d, want %d", inputs, spy.StartSpanInvocations, 1)
	}
}

func TestPostgres_SaveTerminals_ConnectionClosed(t *testing.T) {
	pool, err := store.NewPostgresPool(t.Context(), testConnStr)
	if err != nil {
		t.Fatalf("create postgres connection pool: %v", err)
	}

	spy := telemetrytest.NewSpyEngine()
	adapter := store.NewPostgresAdapter(pool, spy)

	// Close pool to simulate closed connection
	pool.Close()

	inputs := []string{"https://fake.url"}
	err = adapter.SaveTerminalURLs(t.Context(), inputs)

	if err == nil {
		t.Fatalf("SaveTerminalURLs(%q) expected error, got nil", inputs)
	}

	// Ensure that a telemetry span was recorded
	if spy.StartSpanInvocations != 1 {
		t.Errorf("SaveTerminalsURLs(%q) started spans %d, want %d", inputs, spy.StartSpanInvocations, 1)
	}
}
