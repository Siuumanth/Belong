package middleware

// to check if route is authorized or not

import (
	"net/http"

	"gateway/internal/utils"
)

func NewAuthZ() Middleware {
	return utils.MiddlewareFunc(func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			// blank handler for now
			authCtx := r.Context().Value(utils.AuthContextKey)
			if authCtx == nil {
				http.Error(w, "authentication required, gw", http.StatusUnauthorized)
				return
			}

			next.ServeHTTP(w, r)
		})
	})
}
