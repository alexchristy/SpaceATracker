// Package config loads environment variables.
package config

import (
	"time"

	"github.com/caarlos0/env/v11"
)

// Config contains the configured environment variables.
type Config struct {
	// Required
	DatabaseURI      string `env:"DATABASE_URI,required,notEmpty"`
	TerminalIndexURL string `env:"TERMINAL_INDEX_URL,required,notEmpty"`
	ScraperApiKey    string `env:"SCRAPER_API_KEY,required,notEmpty"`

	// Optional
	DiscoveryInterval time.Duration `env:"DISCOVERY_INTERVAL" envDefault:"1h"`
}

// Load configured environment variables.
func Load() (Config, error) {
	return parse(nil)
}

func parse(opts *env.Options) (Config, error) {
	var opt env.Options
	if opts != nil {
		opt = *opts
	}

	var cfg Config
	if err := env.ParseWithOptions(&cfg, opt); err != nil {
		return Config{}, err
	}

	return cfg, nil
}
