package gateway

import (
	MW "gateway/internal/middleware"
)

// deps has all the requrired dependencies
// Dependency injection
type GatewayDeps struct {
	JWT                MW.Middleware
	CORS               MW.Middleware
	SecurityHeaders    MW.Middleware
	Logger             MW.Middleware
	RateLimiter        MW.Middleware
	HeadersInjection   MW.Middleware
	RequestIDGenerator MW.Middleware
}
