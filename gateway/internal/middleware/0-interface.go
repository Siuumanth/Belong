package middleware

import (
	"context"
	"gateway/internal/utils"
	"net/http"
)

type Middleware interface {
	Handle(http.Handler) http.Handler
}

// all middlewares will implement this interface

func GetRequestID(ctx context.Context) string {
	if val := ctx.Value(utils.RequestIDKey); val != nil {
		if id, ok := val.(string); ok {
			return id
		}
	}
	return "unknown"
}
