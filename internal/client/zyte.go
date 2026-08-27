package client

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/trace"
)

// ZyteClientName is the canonical name of the zyte API client for logging and telemetry spans.
const ZyteClientName = "zyte"

// ZyteApiURL points to the zyte client API endpoint.
const ZyteApiURL = "https://api.zyte.com/v1/extract"

type zyteClient struct {
	apiURL     string
	authHeader string
	httpClient *http.Client
	tracer     trace.Tracer
}

// NewZyte returns a new zyte API client for web scraping.
func NewZyte(apiURL, apiKey string, tracer trace.Tracer) *zyteClient {
	auth := base64.StdEncoding.EncodeToString([]byte(apiKey + ":"))

	return &zyteClient{
		apiURL:     apiURL,
		authHeader: "Basic " + auth,
		httpClient: &http.Client{
			Timeout: 15 * time.Second,
		},
		tracer: tracer,
	}
}

type zyteRequest struct {
	URL              string `json:"url"`
	HTTPResponseBody bool   `json:"httpResponseBody"`
	FollowRedirect   bool   `json:"followRedirect"`
}

type zyteResponse struct {
	URL              string `json:"url"`
	StatusCode       int    `json:"statusCode"`
	HTTPResponseBody string `json:"httpResponseBody"`
}

// Get returns HTML from the target URL.
func (c *zyteClient) Get(ctx context.Context, targetURL string) (decodedBytes []byte, err error) {
	// Start telemetry trace
	ctx, span := c.tracer.Start(ctx, ZyteClientName+".Get")
	defer func() {
		if err != nil {
			span.RecordError(err)
			span.SetStatus(codes.Error, err.Error())
		}
		span.End()
	}()

	span.SetAttributes(
		attribute.String("target_url", targetURL),
	)

	reqBody := zyteRequest{
		URL:              targetURL,
		HTTPResponseBody: true,
		FollowRedirect:   true,
	}

	var buf bytes.Buffer
	if err = json.NewEncoder(&buf).Encode(reqBody); err != nil {
		return nil, fmt.Errorf("encode zyte scraper request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.apiURL, &buf)
	if err != nil {
		return nil, fmt.Errorf("create zyte scraper request: %w", err)
	}

	// Add headers
	req.Header.Set("Authorization", c.authHeader)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("execute zyte scraper request: %w", err)
	}
	defer func() {
		_ = resp.Body.Close()
	}()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("zyte scraper response code: %d", resp.StatusCode)
	}

	var apiResp zyteResponse
	if err = json.NewDecoder(resp.Body).Decode(&apiResp); err != nil {
		return nil, fmt.Errorf("decode zyte scraper response: %w", err)
	}

	if apiResp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("target URL response code to zyte scraper: %d", apiResp.StatusCode)
	}

	decodedBytes, err = base64.StdEncoding.DecodeString(apiResp.HTTPResponseBody)
	if err != nil {
		return nil, fmt.Errorf("decode base64 zyte scraper response body: %w", err)
	}

	span.SetAttributes(
		attribute.Int("response_body_length", len(decodedBytes)),
	)

	return decodedBytes, nil
}
