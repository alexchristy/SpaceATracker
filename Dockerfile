# --------------
# Build Stage
# --------------
FROM golang:1.26-alpine AS builder

# Dependencies for user creation and CA certificates
RUN apk update && apk add --no-cache git ca-certificates tzdata && update-ca-certificates

# Create non-root user and group for runtime
RUN adduser -D -u 10001 spaceatrackeruser

WORKDIR /app

# Fetch go dependencies
COPY go.mod go.sum ./
RUN go mod download && go mod verify

# Copy remaining source code
COPY . .

# Compile lean binary
RUN CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
	go build \
	-ldflags="-s -w" \
	-o /bin/worker cmd/worker/*.go

# ----------------
# Runtime Stage
# ----------------
FROM scratch

# Import timezone data and CA certificates from builder
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# Import the non-root user and group from builder
COPY --from=builder /etc/passwd /etc/passwd
COPY --from=builder /etc/group /etc/group

# Copy compiled binary
COPY --from=builder /bin/worker /bin/worker

# Non-root execution
USER spaceatrackeruser

ENTRYPOINT ["/bin/worker"]
