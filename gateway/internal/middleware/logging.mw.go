package middleware

import (
	"gateway/internal/metrics"
	"gateway/internal/utils"
	zlog "gateway/pkg/zlog"
	"net/http"
	"strconv"
	"time"

	"go.uber.org/zap"
)

type responseWriter struct {
	http.ResponseWriter
	status int
	body   []byte
}

func (rw *responseWriter) Write(b []byte) (int, error) {
	rw.body = append(rw.body, b...)
	return rw.ResponseWriter.Write(b)
}
func (rw *responseWriter) WriteHeader(code int) {
	rw.status = code
	rw.ResponseWriter.WriteHeader(code)
}

func NewLogger() Middleware {
	return utils.MiddlewareFunc(func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {

			start := time.Now()

			rw := &responseWriter{
				ResponseWriter: w,
				status:         http.StatusOK, // default
			}

			// start inflight
			metrics.HttpInFlight.Inc() // request started

			next.ServeHTTP(rw, r)

			duration := time.Since(start)
			statusStr := strconv.Itoa(rw.status)

			// ---- METRICS ----
			metrics.HttpRequestsTotal.
				WithLabelValues(r.Method, r.URL.Path, statusStr).
				Inc()

			metrics.HttpRequestDuration.
				WithLabelValues(r.Method, r.URL.Path).
				Observe(duration.Seconds())

			metrics.HttpInFlight.Dec()
			// ------------------

			reqID := GetRequestID(r.Context())

			if rw.status >= 400 {
				zlog.L.Error("Request failed",
					zap.String("request_id", reqID),
					zap.String("method", r.Method),
					zap.String("path", r.URL.Path),
					zap.Int("status", rw.status),
					zap.Duration("duration", duration),
					zap.String("error", string(rw.body)),
				)
			} else {
				zlog.L.Info("Request success",
					zap.String("request_id", reqID),
					zap.String("method", r.Method),
					zap.String("path", r.URL.Path),
					zap.Int("status", rw.status),
					zap.Duration("duration", duration),
				)
			}

		})
	})
}
