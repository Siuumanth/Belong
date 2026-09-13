package middleware

import (
	"context"
	"gateway/internal/utils"
	"net/http"

	"github.com/google/uuid"
)

func NewRequestIDGenerator() Middleware {
	return utils.MiddlewareFunc(func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {

			// 1. generate request ID
			reqID := uuid.NewString()

			// 2. store in context
			ctx := context.WithValue(r.Context(), utils.RequestIDKey, reqID)
			r = r.WithContext(ctx)

			// 3. set on response
			w.Header().Set("X-Request-ID", reqID)

			next.ServeHTTP(w, r)
		})
	})
}
