package middleware

import (
	"gateway/internal/utils"
	"net/http"
)

func NewSecurityHeaders() Middleware {
	return utils.MiddlewareFunc(func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			//Stops browsers from guessing content types (prevents XSS-style attacks)
			w.Header().Set("X-Content-Type-Options", "nosniff")
			// Forces HTTPS for future requests
			w.Header().Set("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
			// Prevents sensitive responses (tokens, user data) from being cached
			w.Header().Set("Cache-Control", "no-store")

			next.ServeHTTP(w, r)
		})
	})
}
