package discovery

import (
	"fmt"
	"io"
	"net/url"
	"path"
	"strings"

	"golang.org/x/net/html"
)

var terminalURLTargets = []string{
	"/amc-travel-site/terminals/",
	"space-a",
	"passenger-terminal",
	"spaceavailabletravel",
	"passenger_terminal",
}

var nonTerminalExclusions = []string{
	"amc-space-available-travel-page",
}

var nonHttpSchemes = map[string]bool{
	"mailto":     true,
	"javascript": true,
}

var staticAssetExtensions = map[string]bool{
	".pdf":  true,
	".png":  true,
	".jpg":  true,
	".jpeg": true,
}

func parseTerminalURLs(r io.Reader) ([]*url.URL, error) {
	// Generally are 65 terminals
	seen := make(map[string]bool, 65)
	links := make([]*url.URL, 0, 65)

	if err := tokenizeAndExtractTerminalLinks(r, seen, &links); err != nil {
		return nil, fmt.Errorf("extracting terminal URLs: %w", err)
	}

	return links, nil
}

// Returns whether a string contains any of the targets case insenstive
func containsAny(input string, targets []string) bool {
	if input == "" || len(targets) == 0 {
		return false
	}

	lowerInput := strings.ToLower(input)
	for _, target := range targets {
		if strings.Contains(lowerInput, target) {
			return true
		}
	}

	return false
}

func tokenizeAndExtractTerminalLinks(r io.Reader, seen map[string]bool, links *[]*url.URL) error {
	z := html.NewTokenizer(r)

	for {
		tt := z.Next()

		switch tt {
		case html.ErrorToken:
			err := z.Err()
			if err == io.EOF {
				return nil
			}
			return fmt.Errorf("extracting terminal links: %w", err)

		case html.StartTagToken, html.SelfClosingTagToken:
			t := z.Token()

			for _, attr := range t.Attr {
				switch attr.Key {
				case "href":
					if t.Data != "a" {
						continue
					}

					// Contains non-terminal string
					if containsAny(attr.Val, nonTerminalExclusions) {
						continue
					}

					// Contains key terminal strings
					if !containsAny(attr.Val, terminalURLTargets) {
						continue
					}

					// Is valid URL
					parsedURL, err := url.Parse(attr.Val)
					if err != nil {
						continue
					}

					// Is an HTTP URL
					if nonHttpSchemes[parsedURL.Scheme] {
						continue
					}

					// Is not a static asset (pdf, jpg, etc.)
					urlExt := path.Ext(parsedURL.Path)
					if staticAssetExtensions[urlExt] {
						continue
					}

					// Deduplicate http/https URLs
					keyURL := *parsedURL
					keyURL.Scheme = ""
					key := strings.ToLower(keyURL.String())
					key = path.Clean("/" + key)

					if !seen[key] {
						seen[key] = true
						*links = append(*links, parsedURL)
					}

				case "data-html":
					if attr.Val == "" {
						continue
					}

					unescapedHTML := html.UnescapeString(attr.Val)
					if err := tokenizeAndExtractTerminalLinks(strings.NewReader(unescapedHTML), seen, links); err != nil {
						return fmt.Errorf("parsing nested data-html: %w", err)
					}

				}
			}
		}

	}
}
