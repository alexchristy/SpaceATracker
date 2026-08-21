// Package discovery discovers active AMC Space-A terminals.
package discovery

import (
	"bytes"
	"context"
	"fmt"
	"log/slog"

	"github.com/alexchristy/SpaceATracker/internal/telemetry"
)

// DiscoveryServiceName is the canonical name of the discovery service in logging and telemetry spans.
const DiscoveryServiceName = "discovery"

// Store defines the persistence contract for discovered terminals.
type Store interface {
	SaveTerminalURLs(ctx context.Context, terminalURLs []string) error
}

// Scraper defines the network fetching contract for retrieving raw web payloads.
type Scraper interface {
	Get(ctx context.Context, URL string) ([]byte, error)
}

// Service orchestrates terminal discovery, URL normalization, and storage.
type Service struct {
	store     Store
	scraper   Scraper
	telemetry telemetry.Engine
	logger    *slog.Logger
}

// NewService constructs a discovery service with required dependencies.
func NewService(store Store, scraper Scraper, tel telemetry.Engine, logger *slog.Logger) *Service {
	return &Service{
		store:     store,
		scraper:   scraper,
		telemetry: tel,
		logger:    logger,
	}
}

// Execute fetches targetURL, discovers active Space-A terminals, and saves normalized results.
func (s *Service) Execute(ctx context.Context, targetURL string) (err error) {
	// Start telemetry trace
	ctx, done := s.telemetry.StartSpan(ctx, DiscoveryServiceName+".Execute")
	defer done(&err)

	// Fetch webpage HTML
	htmlBytes, err := s.scraper.Get(ctx, targetURL)
	if err != nil {
		return fmt.Errorf("scraping terminal index page: %w", err)
	}
	htmlReader := bytes.NewReader(htmlBytes)

	// Parse terminals
	terminalURLs, err := parseTerminalURLs(htmlReader)
	if err != nil {
		return fmt.Errorf("parsing terminal index page: %w", err)
	}

	// Record number terminals found
	s.telemetry.RecordItemCount(ctx, DiscoveryServiceName, "terminal_urls", int64(len(terminalURLs)))

	// Normalize URLs
	urlNormalizer, err := NewURLNormalizer(targetURL)
	if err != nil {
		return fmt.Errorf("initialize URL normalizer: %w", err)
	}

	// Generally about 65 terminals
	normalizedURLs := make([]string, 0, 65)

	for _, terminalURL := range terminalURLs {
		normalizedURLs = append(normalizedURLs, urlNormalizer.Normalize(terminalURL))
	}

	// Store discovered terminals
	if err = s.store.SaveTerminalURLs(ctx, normalizedURLs); err != nil {
		return fmt.Errorf("store discovered terminals: %w", err)
	}

	s.logger.InfoContext(ctx, "terminal discovery finished")

	return nil
}
