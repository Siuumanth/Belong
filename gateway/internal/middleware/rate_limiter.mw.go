package middleware

import (
	"gateway/internal/utils"
	"net"
	"net/http"
	"sync"
	"time"
)

/*
GOAL of this Rate Limiter:
1. Find if the UserID exists for this requests
2. If UserID exists then use it as the key for counting requests
3. If UserID does not exist then increase the request count wrt IP address
*/

// TODO: switch rate limiter to Redis

type RateLimiter interface {
	Allow(key string) bool
}

// this is the basic master logic of the rate limiter, irrespective of the rate limiter implementation
// only the Allow function will differ based on the type of rate limiter implementation
// One middleware, many strategies
func NewRateLimiter(rl RateLimiter) Middleware {
	return utils.MiddlewareFunc(func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {

			key := extractKey(r)
			if !rl.Allow(key) {
				http.Error(w, "Too many requests", http.StatusTooManyRequests)
				return
			}

			next.ServeHTTP(w, r)
		})
	})
}

func extractKey(r *http.Request) string {
	// check for User ID in the context, else fall back to IP
	if auth, ok := r.Context().Value(utils.AuthContextKey).(utils.AuthContext); ok {
		return auth.UserID
	}
	// fallback to IP
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		host = r.RemoteAddr
	}
	return host
}

type BasicRateLimiter struct {
	mu        sync.Mutex
	visitors  map[string]int
	limit     int
	resetTime time.Duration
}

func NewBasicRateLimiter(limit int, resetTime time.Duration) *BasicRateLimiter {
	rl := BasicRateLimiter{
		mu:        sync.Mutex{},
		visitors:  make(map[string]int),
		limit:     limit,
		resetTime: resetTime,
	}
	go rl.resetVisitorCount()

	return &rl
}

// single responsibility
func (rl *BasicRateLimiter) Allow(key string) bool {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	rl.visitors[key]++

	if rl.visitors[key] > rl.limit {
		return false
	}

	return true
}

func (rl *BasicRateLimiter) resetVisitorCount() {
	for {
		time.Sleep(rl.resetTime)
		rl.mu.Lock()
		// assign new map to clear old data
		rl.visitors = make(map[string]int)
		rl.mu.Unlock()
	}
}
