package gateway

import (
	"net/http"
)

func (g *Gateway) BuildGateway(router http.Handler) http.Handler {
	// base handler (router / proxy)

	// apply in REVERSE order
	router = g.headerInjection.Handle(router)
	router = g.rateLimiter.Handle(router)
	router = g.jwt.Handle(router)
	router = g.cors.Handle(router)
	router = g.securityHeaders.Handle(router)
	router = g.logging.Handle(router)
	router = g.requestID.Handle(router) // id generation happen first

	return router
}
