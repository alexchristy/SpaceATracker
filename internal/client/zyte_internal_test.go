package client

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/alexchristy/SpaceATracker/internal/telemetry/telemetrytest"
)

func TestZyte_Get_Success(t *testing.T) {
	t.Parallel()

	fakeApiToken := "fakeApiToken"
	wantResponseBody := []byte("This is not real HTML")

	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		payload := map[string]any{
			"url":              "https://fake.url",
			"statusCode":       http.StatusOK,
			"httpResponseBody": base64.StdEncoding.EncodeToString(wantResponseBody),
		}

		// Zyte API requires the trailing colon
		want := fmt.Sprintf("Basic %s:", fakeApiToken)

		authHeader := r.Header.Get("Authorization")
		splitHeader := strings.Split(authHeader, " ")
		token, err := base64.StdEncoding.DecodeString(splitHeader[1])
		if err != nil {
			t.Errorf("decode zyte client authorization header: %v", err)
		}

		got := fmt.Sprintf("Basic %s", token)
		if got != want {
			t.Errorf("Authorization header = %q, want %q", got, want)
		}

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_ = json.NewEncoder(w).Encode(payload)
	}))
	defer ts.Close()

	spy := telemetrytest.NewSpyEngine()
	client := NewZyte(ts.URL, fakeApiToken, spy)

	got, err := client.Get(context.Background(), "https://fake.url")
	if err != nil {
		t.Errorf("Get() unexpected error: %v", err)
	}

	if !bytes.Equal(got, wantResponseBody) {
		t.Errorf("Get() = %q, want %q", string(got), string(wantResponseBody))
	}

	// Verify telemetry span was recorded
	if spy.StartSpanInvocations != 1 {
		t.Errorf("Get() started spans %d, want %d", spy.StartSpanInvocations, 1)
	}
}

func TestZyte_Get_Error(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name       string
		mockServer func(w http.ResponseWriter, r *http.Request)
		ctxTimeout time.Duration
	}{
		{
			name: "non 200 status code from zyte",
			mockServer: func(w http.ResponseWriter, r *http.Request) {
				w.WriteHeader(http.StatusInternalServerError)
			},
			ctxTimeout: 1 * time.Second,
		},
		{
			name: "non 200 status code from target URL",
			mockServer: func(w http.ResponseWriter, r *http.Request) {
				payload := map[string]any{
					"url":              "https://fake.url",
					"statusCode":       http.StatusInternalServerError,
					"httpResponseBody": base64.StdEncoding.EncodeToString([]byte("body")),
				}

				w.WriteHeader(http.StatusOK)
				w.Header().Set("Content-Type", "application/json")
				_ = json.NewEncoder(w).Encode(payload)
			},
			ctxTimeout: 1 * time.Second,
		},
		{
			name: "invalid zyte response",
			mockServer: func(w http.ResponseWriter, r *http.Request) {
				w.WriteHeader(http.StatusOK)
				w.Header().Set("Content-Type", "application/json")
				_, _ = w.Write([]byte(`{"broken_payload": `))
			},
			ctxTimeout: 1 * time.Second,
		},
		{
			name: "invalid base64 encoded http response body",
			mockServer: func(w http.ResponseWriter, r *http.Request) {
				w.WriteHeader(http.StatusOK)
				w.Header().Set("Content-Type", "application/json")
				payload := map[string]any{
					"url":              "https://fake.url",
					"statusCode":       http.StatusOK,
					"httpResponseBody": "invalid base64 %^%&$",
				}
				_ = json.NewEncoder(w).Encode(payload)
			},
			ctxTimeout: 1 * time.Second,
		},
		{
			name: "transport timeout",
			mockServer: func(w http.ResponseWriter, r *http.Request) {
				time.Sleep(50 * time.Millisecond)
				w.WriteHeader(http.StatusOK)
			},
			ctxTimeout: 5 * time.Millisecond,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			ts := httptest.NewServer(http.HandlerFunc(tt.mockServer))
			defer ts.Close()

			client := NewZyte(ts.URL, "fakeApiToken", telemetrytest.NewSpyEngine())
			ctx, cancel := context.WithTimeout(context.Background(), tt.ctxTimeout)
			defer cancel()

			_, err := client.Get(ctx, "https://fake.url")
			if err == nil {
				t.Fatal("Get() error = nil, wantErr true")
			}
		})
	}
}
