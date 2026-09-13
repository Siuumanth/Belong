package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
)

var (
	HttpRequestsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "http_requests_total",
			Help: "Total number of HTTP requests",
		},
		[]string{"method", "path", "status"},
	)

	HttpRequestDuration = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name: "http_request_duration_seconds",
			Help: "Duration of HTTP requests",
			// Custom buckets to catch everything from 5ms to 60s
			Buckets: []float64{
				.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 7.5, 10, 15, 20, 30, 45, 60,
			},
		},
		[]string{"method", "path"},
	)
	HttpInFlight = prometheus.NewGauge(
		prometheus.GaugeOpts{
			Name: "http_in_flight_requests",
			Help: "Current number of in-flight HTTP requests",
		},
	)
)

func Init() {
	prometheus.MustRegister(HttpRequestsTotal)
	prometheus.MustRegister(HttpRequestDuration)
	prometheus.MustRegister(HttpInFlight)
}
