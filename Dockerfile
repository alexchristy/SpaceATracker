# --------------
# Build Stage
# --------------
FROM golang:1.26-alpine AS builder

# Dependencies for user creation and CA certificates
RUN apk update && apk add --no-cache git ca-certificates tzdata && update-ca-certificates

# Install migration tools
RUN go install -tags "postgres" github.com/golang-migrate/migrate/v4/cmd/migrate@latest

# Create non-root user and group for runtime
RUN adduser -D -u 10001 spaceatrackeruser

WORKDIR /app

# Fetch go dependencies
COPY go.mod go.sum ./
RUN go mod download && go mod verify

# Copy remaining source code
COPY . .

# Compile lean binary
RUN CGO_ENABLED=0 GOOS=linux \
	go build \
	-ldflags="-s -w" \
	-o /bin/worker cmd/worker/*.go

# ----------------
# Runtime Stage
# ----------------
FROM alpine:latest

# Dependenceies for CA certificates
RUN apk add --no-cache ca-certificates tzdata

# Import the non-root user and group from builder
COPY --from=builder /etc/passwd /etc/passwd
COPY --from=builder /etc/group /etc/group

# Copy compiled binary
COPY --from=builder /bin/worker /bin/worker

# Copy migration dependencies
COPY --from=builder /go/bin/migrate /bin/migrate
COPY db/migrations /db/migrations

# Non-root execution
USER spaceatrackeruser
