package proxy

import (
	"encoding/json"
	"fmt"
	"gateway/internal/middleware"
	"gateway/pkg/zlog"
	"net/http"
	"net/http/httputil"
	"net/url"
	"time"

	"github.com/sony/gobreaker"
	"go.uber.org/zap"
)

type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (rw *statusRecorder) WriteHeader(code int) {
	if rw.status == 0 || rw.status == http.StatusOK {
		rw.status = code
	}
	rw.ResponseWriter.WriteHeader(code)
}
func NewReverseProxy(target string, serviceName string) http.Handler {
	u, err := url.Parse(target)
	if err != nil {
		panic(err)
	}

	proxy := httputil.NewSingleHostReverseProxy(u)

	settings := gobreaker.Settings{
		Name:        serviceName,
		MaxRequests: 5,                // max trial req in half open state
		Interval:    10 * time.Second, // count in intervals of this sec
		Timeout:     30 * time.Second, // wait this much after open to go to half open
		ReadyToTrip: func(counts gobreaker.Counts) bool {
			if counts.Requests < 10 {
				return false
			}
			ratio := float64(counts.TotalFailures) / float64(counts.Requests)
			return ratio >= 0.6 // trip when 60 percent of requests fail
		},

		OnStateChange: func(name string, from, to gobreaker.State) {
			zlog.L.Info("circuit breaker state change",
				zap.String("cb_name", name),
				zap.String("from", from.String()),
				zap.String("to", to.String()),
			)
		}, // log wen state change
	}

	cb := gobreaker.NewCircuitBreaker(settings)

	// Capture upstream transport errors (dial, timeout, etc.)
	// Upstream error happens when the gateway cannot even successfully talk to the backend service.
	// default respnose is 502, we just handle it and log it how we want here
	// internal/proxy/reverse.go

	proxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
		reqID := middleware.GetRequestID(r.Context())
		zlog.L.Error("upstream error",
			zap.String("request_id", reqID),
			zap.String("cb_name", serviceName),
			zap.Error(err), // Automatically handles the error message
		)

		// Explicitly set the status code before writing the message
		w.WriteHeader(http.StatusBadGateway)
		json.NewEncoder(w).Encode(struct {
			Error string `json:"error"`
		}{
			Error: "Upstream error: Service unreachable",
		})
	}

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		rw := &statusRecorder{
			ResponseWriter: w,
			status:         0, // Start at 0 to detect if it's been set
		}

		_, err := cb.Execute(func() (interface{}, error) {
			proxy.ServeHTTP(rw, r)

			if rw.status >= 500 {
				return nil, fmt.Errorf("upstream failure: %d", rw.status)
			}
			return nil, nil
		})

		if err != nil {
			// If headers are already written by proxy.ErrorHandler, just return
			// We check this by seeing if our statusRecorder was touched
			if err == gobreaker.ErrOpenState {
				w.WriteHeader(http.StatusServiceUnavailable)
				json.NewEncoder(w).Encode(map[string]string{"error": "Circuit open"})
				return
			}

			// Only write if the proxy hasn't already sent a response
			// This prevents the "200 OK" default behavior
			if rw.status == 0 {
				w.WriteHeader(http.StatusBadGateway)
				json.NewEncoder(w).Encode(map[string]string{"error": "Upstream unreachable"})
			}
			return
		}
	})
}
