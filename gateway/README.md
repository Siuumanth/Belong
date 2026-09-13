# Belong Go API Gateway

The Go API Gateway is the public-facing entry point for Belong clients (Web/Mobile/CLI).

## Directory Structure
- `cmd/`: Application entrypoints (e.g., `cmd/gateway/main.go` or `cmd/main.go`)
- `internal/`: Internal private application packages (e.g., routing, middleware, auth, config)
- `go.mod`: Go module definition (`belong/go-gateway`)

## Responsibilities
- Authentication verification (collaborating with the Go Auth service)
- Request routing and reverse proxying to the Python Belong service
- CORS configuration
- Rate limiting and client telemetry
