package config

import (
	"testing"
	"time"

	"github.com/caarlos0/env/v11"
)

func defaultValidEnvOpts() env.Options {
	return env.Options{
		Environment: map[string]string{
			"DATABASE_URI":       "postgresql://username:hellothere@hostname:port/database_name?option=value",
			"TERMINAL_INDEX_URL": "https://www.example.com",
			"SCRAPER_API_KEY":    "this-is-a-fake-api-key",
			"DISCOVERY_INTERVAL": "1s",
		},
	}
}

func Test_parse(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name     string
		mutate   func(opts *env.Options) // Inject changes to default
		wantErr  bool
		validate func(t *testing.T, cfg Config)
	}{
		{
			name:    "valid baseline executes successfully",
			mutate:  func(opts *env.Options) {}, // No mutation
			wantErr: false,
		},
		{
			name: "missing terminal index URL",
			mutate: func(opts *env.Options) {
				delete(opts.Environment, "TERMINAL_INDEX_URL")
			},
			wantErr: true,
		},
		{
			name: "empty terminal index URL",
			mutate: func(opts *env.Options) {
				opts.Environment["TERMINAL_INDEX_URL"] = ""
			},
			wantErr: true,
		},
		{
			name: "missing discovery interval populates default value",
			mutate: func(opts *env.Options) {
				delete(opts.Environment, "DISCOVERY_INTERVAL")
			},
			wantErr: false,
			validate: func(t *testing.T, cfg Config) {
				if cfg.DiscoveryInterval != 1*time.Hour {
					t.Errorf("expected default 1h, got %v", cfg.DiscoveryInterval)
				}
			},
		},
		{
			name: "missing scraper api key",
			mutate: func(opts *env.Options) {
				delete(opts.Environment, "SCRAPER_API_KEY")
			},
			wantErr: true,
		},
		{
			name: "empty scraper api key",
			mutate: func(opts *env.Options) {
				opts.Environment["SCRAPER_API_KEY"] = ""
			},
			wantErr: true,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			opts := defaultValidEnvOpts()
			tc.mutate(&opts)

			// Check error state
			cfg, err := parse(&opts)
			if (err != nil) != tc.wantErr {
				t.Errorf("parse() error = %v, wantErr %v", err, tc.wantErr)
			}

			// Check data state
			if err == nil && tc.validate != nil {
				tc.validate(t, cfg)
			}
		})
	}
}
