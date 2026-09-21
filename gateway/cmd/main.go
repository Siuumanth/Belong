package main

import (
	"context"
	"fmt"
	"gateway/internal/gateway"
	"gateway/internal/metrics"
	MW "gateway/internal/middleware"
	"gateway/internal/router"

	"gateway/pkg/zlog"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/joho/godotenv"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.uber.org/zap"
)

func main() {
	zlog.Init()
	defer zlog.Sync()

	fmt.Println("=========================================")
	fmt.Println("      Starting Belong API Gateway        ")
	fmt.Println("=========================================")

	metrics.Init()
	_ = godotenv.Load(".env")
	_ = godotenv.Load("../.env")

	port := os.Getenv("PORT")
	if port == "" {
		port = "9000"
	}

	disableAuth := os.Getenv("DISABLE_AUTH") == "true" || os.Getenv("DISABLE_AUTH") == "1"
	if disableAuth {
		fmt.Println("[CONFIG] DISABLE_AUTH=true (Gateway JWT Verification Bypass ACTIVE)")
	} else {
		fmt.Println("[CONFIG] DISABLE_AUTH=false (JWT Authentication Enforced)")
	}


	rl := MW.NewBasicRateLimiter(100000, time.Minute)
	authz := MW.NewAuthZ()

	gatewayDeps := &gateway.GatewayDeps{
		JWT:                MW.NewJWT(),
		CORS:               MW.NewCORS(),
		SecurityHeaders:    MW.NewSecurityHeaders(),
		Logger:             MW.NewLogger(),
		RateLimiter:        MW.NewRateLimiter(rl),
		HeadersInjection:   MW.NewHeadersInjection(),
		RequestIDGenerator: MW.NewRequestIDGenerator(),
	}
	gw := gateway.NewGateway(gatewayDeps)
	proxies := router.NewProxies()
	r := router.NewChiRouter()
	r.ConfigureRoutes(proxies, authz)

	finalGateway := gw.BuildGateway(r)

	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.Handler())
	mux.Handle("/", finalGateway)

	server := &http.Server{
		Addr:    ":" + port,
		Handler: mux,
	}

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)

	go func() {
		fmt.Printf("[OK] Belong API Gateway is READY and listening on port :%s\n", port)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			zlog.L.Error("Listen error: %v\n", zap.Error(err))
		}
	}()

	<-stop

	fmt.Println("\nShutting down Gateway gracefully...")
	ctx, cancel := context.WithTimeout(context.Background(), 6*time.Second)
	defer cancel()

	if err := server.Shutdown(ctx); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}

	fmt.Println("Gateway exiting cleanly")
}
