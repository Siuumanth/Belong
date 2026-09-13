package gateway

import (
	MW "gateway/internal/middleware"
)

/*
Middlewares order:
Logging
SecurityHeaders
CORS
JWT (only for protected routes)
RateLimit
HeaderInjection (only before proxy)
↓
Handler / Proxy

*/

// we will implement our MW chain using an explicit pipeline
// we could do by wrapping MW functions, but that would be harder to understand

type Gateway struct {
	jwt             MW.Middleware
	cors            MW.Middleware
	securityHeaders MW.Middleware
	logging         MW.Middleware
	rateLimiter     MW.Middleware
	headerInjection MW.Middleware
	requestID       MW.Middleware
}

func NewGateway(deps *GatewayDeps) *Gateway {
	return &Gateway{
		jwt:             deps.JWT,
		cors:            deps.CORS,
		securityHeaders: deps.SecurityHeaders,
		logging:         deps.Logger,
		rateLimiter:     deps.RateLimiter,
		headerInjection: deps.HeadersInjection,
		requestID:       deps.RequestIDGenerator,
	}
}
