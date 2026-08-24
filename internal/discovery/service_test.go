package discovery_test

import (
	"context"
	"errors"
	"log/slog"
	"testing"

	"github.com/alexchristy/SpaceATracker/internal/discovery"
	"github.com/alexchristy/SpaceATracker/internal/telemetry/telemetrytest"
)

type AlwaysStores struct{}

func (AlwaysStores) SaveTerminalURLs(ctx context.Context, terminalURLs []string) error {
	return nil
}

type NeverStores struct {
	err error
}

func (n NeverStores) SaveTerminalURLs(ctx context.Context, terminalURLs []string) error {
	return n.err
}

type AlwaysScrapes struct{}

func (AlwaysScrapes) Get(ctx context.Context, url string) ([]byte, error) {
	return []byte{}, nil
}

type NeverScrapes struct {
	err error
}

func (n NeverScrapes) Get(ctx context.Context, url string) ([]byte, error) {
	return nil, n.err
}

func TestExecute_Error(t *testing.T) {
	t.Parallel()

	storeError := errors.New("fake store error")
	scraperError := errors.New("fake scraper error")

	tests := []struct {
		name         string
		store        discovery.Store
		scraper      discovery.Scraper
		targetURL    string
		wantSentinel error
	}{
		{
			name:         "scraper error",
			store:        AlwaysStores{},
			scraper:      NeverScrapes{err: scraperError},
			targetURL:    "https://fake.terminal-index.url",
			wantSentinel: scraperError,
		},
		{
			name:         "store error",
			store:        NeverStores{err: storeError},
			scraper:      AlwaysScrapes{},
			targetURL:    "https://fake.terminal-index.url",
			wantSentinel: storeError,
		},
		{
			name:         "terminal URL parsing error",
			store:        AlwaysStores{},
			scraper:      AlwaysScrapes{},
			targetURL:    "ht@tps://broken.url",
			wantSentinel: nil,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			discardLogger := slog.New(slog.DiscardHandler)
			spy := telemetrytest.NewSpyEngine()
			worker := discovery.NewService(
				tt.store,
				tt.scraper,
				spy,
				discardLogger,
			)

			err := worker.Execute(context.Background(), tt.targetURL)

			if err == nil {
				t.Fatalf("Execute(%q) expected error, got nil", tt.targetURL)
			}

			if tt.wantSentinel != nil && !errors.Is(err, tt.wantSentinel) {
				t.Errorf("Execute(%q) error = %v, want %v", tt.targetURL, err, tt.wantSentinel)
			}

			// Should record one span every execution
			if spy.StartSpanInvocations != 1 {
				t.Errorf("Execute(%q) stated spans %d, want %d", tt.targetURL, spy.StartSpanInvocations, 1)
			}
		})
	}
}
