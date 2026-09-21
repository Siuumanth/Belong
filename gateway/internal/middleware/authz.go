package middleware

// to check if route is authorized or not

import (
	"net/http"
	"os"

	"gateway/internal/utils"
)

func NewAuthZ() Middleware {
	return utils.MiddlewareFunc(func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			disableAuth := os.Getenv("DISABLE_AUTH") == "true" || os.Getenv("DISABLE_AUTH") == "1"
			if disableAuth {
				next.ServeHTTP(w, r)
				return
			}

			authCtx := r.Context().Value(utils.AuthContextKey)
			if authCtx == nil {
				http.Error(w, "authentication required, gw", http.StatusUnauthorized)
				return
			}

			next.ServeHTTP(w, r)
		})
	})
}

