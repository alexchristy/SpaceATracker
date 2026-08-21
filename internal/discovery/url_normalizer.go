package discovery

import (
	"fmt"
	"net/url"
	"path"
	"strings"
)

// URLNormalizer facilitates URL normalization based on a referer/base URL.
type URLNormalizer struct {
	u        *url.URL
	basePath string
}

// NewURLNormalizer constructs a URL normalizer for a specific referer/base URL.
func NewURLNormalizer(terminalIndexURL string) (*URLNormalizer, error) {
	parsed, err := url.Parse(terminalIndexURL)
	if err != nil {
		return nil, fmt.Errorf("parse raw URL: %w", err)
	}

	if parsed.Scheme == "" || parsed.Host == "" {
		return nil, fmt.Errorf("URL %q missing scheme or host", terminalIndexURL)
	}

	// Empty paths become '/'
	basePath := path.Clean("/" + parsed.Path)

	// Extract the first directory in the path
	if basePath != "/" {
		parts := strings.Split(basePath, "/")
		basePath = path.Clean("/" + parts[1])
	}

	return &URLNormalizer{
		u:        parsed,
		basePath: basePath,
	}, nil
}

// Normalize standardizes mixed relative and absolute URLs based on the configured referer/base URL.
func (n *URLNormalizer) Normalize(target *url.URL) string {
	// Convert to absolute URL
	if !target.IsAbs() && !strings.HasPrefix(target.Path, n.basePath) {
		target.Path = path.Clean(n.basePath + "/" + target.Path)
	}

	return n.u.ResolveReference(target).String()
}
