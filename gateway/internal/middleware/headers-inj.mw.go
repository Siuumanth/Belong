package middleware

import (
	"gateway/internal/utils"
	"net/http"
	"os"
	"time"
)

/*
Goal of this middleware:

type AuthContext struct {
	UserID   string
	Username string
	Email    string
	Expires  time.Time
}

get these context values and add them to the header
- main thing is userID
*/

func NewHeadersInjection() Middleware {
	return utils.MiddlewareFunc(func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			disableAuth := os.Getenv("DISABLE_AUTH") == "true" || os.Getenv("DISABLE_AUTH") == "1"

			authCtx, ok := utils.GetAuthContext(r.Context())
			if ok {
				r.Header.Set("X-User-ID", authCtx.UserID)

				if !authCtx.Expires.IsZero() {
					r.Header.Set(
						"X-Auth-Expires",
						authCtx.Expires.UTC().Format(time.RFC3339),
					)
				}
			} else if !disableAuth {
				// delete headers for security only if auth is enabled
				r.Header.Del("X-User-ID")
				r.Header.Del("X-Auth-Expires")
			}
			// If disableAuth is true and no JWT authCtx, preserve any client-supplied X-User-ID header

			reqID := GetRequestID(r.Context()) // from logger
			r.Header.Set("X-Request-ID", reqID)
			next.ServeHTTP(w, r)
		})
	})
}

