package middleware

import (
	"gateway/internal/utils"
	"net/http"
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

get these context values and addd them to the header
- main thing is userID and
*/

func NewHeadersInjection() Middleware {
	return utils.MiddlewareFunc(func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			// delete headers for security
			r.Header.Del("X-User-ID")
			r.Header.Del("X-Auth-Expires")

			authCtx, ok := utils.GetAuthContext(r.Context())
			// we assume the previous MW have handled missing fields
			if ok {
				r.Header.Set("X-User-ID", authCtx.UserID)

				if !authCtx.Expires.IsZero() {
					r.Header.Set(
						"X-Auth-Expires",
						authCtx.Expires.UTC().Format(time.RFC3339),
					)
				}
			}

			reqID := GetRequestID(r.Context()) // from logger
			r.Header.Set("X-Request-ID", reqID)
			next.ServeHTTP(w, r)
		})
	})
}
