package config_test

import (
	"testing"

	"github.com/alexchristy/SpaceATracker/internal/config"
)

func TestLoad(t *testing.T) {
	// Happy path
	t.Run("valid environment succeeds", func(t *testing.T) {
		t.Setenv("DATABASE_URI", "postgres://mock")
		t.Setenv("TERMINAL_INDEX_URL", "https://www.example.com")
		t.Setenv("SCRAPER_API_KEY", "fake-api-key")

		if _, err := config.Load(); err != nil {
			t.Fatalf("expected Load to succeed, got %v", err)
		}
	})

	// Unhappy path
	t.Run("invalid environment propagates error", func(t *testing.T) {
		t.Setenv("DATABASE_URI", "")

		if _, err := config.Load(); err == nil {
			t.Fatal("expected Load to propagate validation error, got nil")
		}
	})
}
