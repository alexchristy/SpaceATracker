// Package discovery discovers active AMC Space-A terminals.
package discovery

import (
	"bytes"
	"context"
	"fmt"
	"log/slog"

	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/trace"
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
	store   Store
	scraper Scraper
	tracer  trace.Tracer
	logger  *slog.Logger
}

// NewService constructs a discovery service with required dependencies.
func NewService(store Store, scraper Scraper, tracer trace.Tracer, logger *slog.Logger) *Service {
	return &Service{
		store:   store,
		scraper: scraper,
		tracer:  tracer,
		logger:  logger,
	}
}

// Execute fetches targetURL, discovers active Space-A terminals, and saves normalized results.
func (s *Service) Execute(ctx context.Context, targetURL string) (err error) {
	// Start telemetry trace
	ctx, span := s.tracer.Start(ctx, DiscoveryServiceName+".Execute")
	defer func() {
		if err != nil {
			span.RecordError(err)
			span.SetStatus(codes.Error, err.Error())
		}
		span.End()
	}()

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

	// Record number of discovered terminals
	span.SetAttributes(
		attribute.Int("terminals_found", len(terminalURLs)),
	)

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
