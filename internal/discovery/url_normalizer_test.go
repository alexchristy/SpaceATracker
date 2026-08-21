package discovery_test

import (
	"net/url"
	"testing"

	"github.com/alexchristy/SpaceATracker/internal/discovery"
)

func initURLNormalizer(t *testing.T, terminalIndexURL string) *discovery.URLNormalizer {
	t.Helper()

	n, err := discovery.NewURLNormalizer(terminalIndexURL)
	if err != nil {
		t.Fatalf("initialize URL normalizer: %v", err)
	}

	return n
}

func TestNewURLNormalizer_Success(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name     string
		indexURL string
	}{
		{
			name:     "valid url",
			indexURL: "https://www.example.com/valid",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			_, err := discovery.NewURLNormalizer(tt.indexURL)
			if err != nil {
				t.Fatalf("NewURLNormalizer(%q) unexpected error: %v", tt.indexURL, err)
			}
		})
	}
}

func TestNewURLNormalizer_Error(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name     string
		indexURL string
	}{
		{
			name:     "invalid url",
			indexURL: "ht@tp://example.com",
		},
		{
			name:     "url missing scheme",
			indexURL: "//www.example.com/has/no/scheme",
		},
		{
			name:     "url missing host",
			indexURL: "https://",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			if _, err := discovery.NewURLNormalizer(tt.indexURL); err == nil {
				t.Errorf("NewURLNormalizer(%q) expected error, got nil", tt.indexURL)
			}
		})
	}
}

func TestNormalize_Success(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name     string
		target   string
		indexURL string
		want     string
	}{
		{
			name:     "incomplete relative URL",
			target:   "Terminals/SOUTHCOM-Terminals/Naval-Station-Guantanamo-Bay-Passenger-Terminal/",
			indexURL: "https://www.amc.af.mil/AMC-Travel-Site/AMC-Space-Available-Travel-Page/",
			want:     "https://www.amc.af.mil/AMC-Travel-Site/Terminals/SOUTHCOM-Terminals/Naval-Station-Guantanamo-Bay-Passenger-Terminal",
		},
		{
			name:     "absolute url with same origin",
			target:   "https://www.amc.af.mil/AMC-Travel-Site/Terminals/EUCOM-Terminals/Lajes-Field-AB-Passenger-Terminal/",
			indexURL: "https://www.amc.af.mil/AMC-Travel-Site/AMC-S    pace-Available-Travel-Page/",
			want:     "https://www.amc.af.mil/AMC-Travel-Site/Terminals/EUCOM-Terminals/Lajes-Field-AB-Passenger-Terminal/",
		},
		{
			name:     "absolute url with diff origin",
			target:   "https://www.mcasiwakuni.marines.mil/Organizations/Station/AMC-Passenger-Terminal/",
			indexURL: "https://www.amc.af.mil/AMC-Travel-Site/AMC-S    pace-Available-Travel-Page/",
			want:     "https://www.mcasiwakuni.marines.mil/Organizations/Station/AMC-Passenger-Terminal/",
		},
		{
			name:     "complete relative url",
			target:   "/AMC-Travel-Site/Terminals/CONUS-Terminals/Baltimore-Washington-International-Airport-Passenger-Terminal/",
			indexURL: "https://www.amc.af.mil/AMC-Travel-Site/AMC-S    pace-Available-Travel-Page/",
			want:     "https://www.amc.af.mil/AMC-Travel-Site/Terminals/CONUS-Terminals/Baltimore-Washington-International-Airport-Passenger-Terminal/",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			n := initURLNormalizer(t, tt.indexURL)

			parsedTarget, err := url.Parse(tt.target)
			if err != nil {
				t.Fatalf("parse test target URL: %v", err)
			}

			got := n.Normalize(parsedTarget)

			if got != tt.want {
				t.Errorf("Normalize(%v) = %v, want %v", tt.target, got, tt.want)
			}
		})
	}
}
