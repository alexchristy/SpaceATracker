package discovery

import (
	"bytes"
	"errors"
	"io"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"testing/iotest"

	"github.com/google/go-cmp/cmp"
	"github.com/google/go-cmp/cmp/cmpopts"
)

const testDataDir = "testdata/"

func loadTestFile(t *testing.T, dir, filename string) []byte {
	t.Helper()

	cleanPath := filepath.Clean(filepath.Join(dir, filename))
	data, err := os.ReadFile(cleanPath)
	if err != nil {
		t.Fatalf("load test file: %q", filename)
	}

	return data
}

func loadTestTerminalURLsWantFile(t *testing.T, dir, filename string) []*url.URL {
	t.Helper()

	cleanPath := filepath.Clean(filepath.Join(dir, filename))
	data, err := os.ReadFile(cleanPath)
	if err != nil {
		t.Fatalf("load terminal URLs want file %q: %v", filename, err)
	}

	content := strings.TrimSpace(string(data))
	if content == "" {
		t.Fatal("load terminal URLs want file empty")
	}

	// Generally about 65 terminals
	terminalURLs := make([]*url.URL, 0, 65)
	for _, testURL := range strings.Split(content, "\n") {
		parsedURL, err := url.Parse(testURL)
		if err != nil {
			t.Fatalf("parse test terminal URL %q from %q: %v", testURL, filename, err)
		}

		terminalURLs = append(terminalURLs, parsedURL)
	}

	return terminalURLs
}

func TestContainsAny(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name    string
		input   string
		targets []string
		want    bool
	}{
		{
			name:  "empty string",
			input: "",
			targets: []string{
				"target1",
				"target2",
			},
			want: false,
		},
		{
			name:    "empty targets",
			input:   "this is a string",
			targets: []string{},
			want:    false,
		},
		{
			name:  "finds targets",
			input: "this is a string",
			targets: []string{
				"this",
				"string",
			},
			want: true,
		},
		{
			name:  "finds case insenstive targets",
			input: "This Is A String",
			targets: []string{
				"this",
				"string",
			},
			want: true,
		},
		{
			name:  "contains no targets",
			input: "come down and waste away with me",
			targets: []string{
				"this",
				"string",
			},
			want: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			got := containsAny(tt.input, tt.targets)

			if got != tt.want {
				t.Errorf("containsAny(%v) = %v, want %v", tt.input, got, tt.want)
			}
		})
	}
}

func TestParseTerminalURLs_Success(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name                 string
		htmlFile             string
		terminalURLsWantFile string
	}{
		{
			name:                 "parse_terminal_index_page_07-31-2026",
			htmlFile:             "terminal_index_page_20260731.html",
			terminalURLsWantFile: "terminal_index_page_20260731_want.txt",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			htmlBytes := loadTestFile(t, testDataDir, tt.htmlFile)

			got, err := parseTerminalURLs(bytes.NewReader(htmlBytes))
			if err != nil {
				t.Fatalf("parseTerminalURLs(htmlFile: %q) unexpected error: %v", tt.htmlFile, err)
			}

			want := loadTestTerminalURLsWantFile(t, testDataDir, tt.terminalURLsWantFile)

			// Less function for lexicographical string comparisons
			stringLess := func(a, b *url.URL) bool { return a.String() < b.String() }

			// Sort copy of slices before diff
			opt := cmpopts.SortSlices(stringLess)

			if diff := cmp.Diff(want, got, opt); diff != "" {
				t.Errorf("parseTerminalURLs() mismatch:\n%s", diff)
			}
		})
	}
}

func TestParseTerminalURLs_Error(t *testing.T) {
	t.Parallel()

	simulatedErr := errors.New("simulated read failure")

	tests := []struct {
		name    string
		input   io.Reader
		wantErr error
	}{
		{
			name:    "handle tokenizer error",
			input:   iotest.ErrReader(simulatedErr),
			wantErr: simulatedErr,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			_, err := parseTerminalURLs(tt.input)
			if err == nil {
				t.Error("parseTerminalURLs() expected error, got nil")
			}

			if !errors.Is(err, tt.wantErr) {
				t.Errorf("parseTerminalURLs() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestTokenizeAndExtractTerminalLinks(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name string
		html string
		want []*url.URL
	}{
		{
			name: "skips unparseable urls",
			html: `<a href="https://example.com/space-a/%ZZ">Malformed Link</a>`,
			want: []*url.URL{},
		},
		{
			name: "empty data-html attribute",
			html: `<a href="/cars/non-terminal-url" data-html="">Valid Link</a>`,
			want: []*url.URL{},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			r := strings.NewReader(tt.html)
			seen := make(map[string]bool, 1)
			links := make([]*url.URL, 0, 1)

			err := tokenizeAndExtractTerminalLinks(r, seen, &links)
			if err != nil {
				t.Fatalf("tokenizeAndExtractTerminalLinks(%v) unexpected error: %v", tt.html, err)
			}

			if diff := cmp.Diff(tt.want, links); diff != "" {
				t.Errorf("tokenizeAndExtractTerminalLinks() mismatch:\n%s", diff)
			}
		})
	}
}
