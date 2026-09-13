package middleware

import (
	"gateway/internal/utils"
	"net/http"
	"os"
)

// Allowed origins
var allowedOrigins []string

func NewCORS() Middleware {
	// runs once at startup
	allowedOrigins = []string{
		os.Getenv("FRONTEND_URL"),
		os.Getenv("DEV_URL"),
		"http://localhost:5500",
		"https://localhost:5500",
		"http://127.0.0.1:5500",
		os.Getenv("OTHER_URL"),
	}
	return utils.MiddlewareFunc(func(next http.Handler) http.Handler {
		// Take that function value and treat it as a MiddlewareFunc
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { // now tihs function becomes a http.handler because we are wrapping it in http.HanderFunc

			origin := r.Header.Get("Origin")
			// fmt.Println(origin)
			if origin == "" {
				next.ServeHTTP(w, r) // no header means continue
				return
			}
			if origin != "" && !isOriginAllowed(origin) {
				http.Error(w, "CORS blocked", http.StatusForbidden)
				return
			}

			if isOriginAllowed(origin) {
				w.Header().Set("Access-Control-Allow-Origin", origin)
			}

			// Set other CORS headers
			// this means allow these types of errors
			w.Header().Set("Access-Control-Allow-Headers", "Accept, Content-Type, Content-Length, Authorization, Upload-UUID, Checksum")
			w.Header().Set("Access-Control-Expose-Headers", "Authorization")
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE")
			w.Header().Set("Access-Control-Allow-Credentials", "true")
			w.Header().Set("Access-Control-Max-Age", "10800")

			// Handle preflight request
			if r.Method == http.MethodOptions {
				w.WriteHeader(http.StatusNoContent)
				return
			}

			next.ServeHTTP(w, r)
		})
	})
}

func isOriginAllowed(origin string) bool {
	for _, allowedOrigin := range allowedOrigins {
		if origin == allowedOrigin {
			return true
		}
	}
	return false
}
