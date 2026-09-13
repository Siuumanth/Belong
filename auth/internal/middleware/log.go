package middleware

import "net/http"

func LogRequestId(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		id := r.Header.Get("X-Request-ID")
		if id != "" {

		}

		next.ServeHTTP(w, r)
	})
}
