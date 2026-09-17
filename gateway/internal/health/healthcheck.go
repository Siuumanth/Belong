package health

import (
	"encoding/json"
	"net/http"
	"os"
	"time"
)

type ServiceStatus struct {
	Name    string `json:"name"`
	Status  string `json:"status"`
	Message string `json:"message,omitempty"`
}

type HealthResponse struct {
	Status   string          `json:"status"`
	Services []ServiceStatus `json:"services"`
}

func getEnv(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return fallback
}

func checkService(url string, timeout time.Duration) (string, string) {
	client := http.Client{
		Timeout: timeout,
	}
	resp, err := client.Get(url)
	if err != nil {
		return "down", err.Error()
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		return "up", ""
	}
	return "unhealthy", resp.Status
}

func HealthCheckHandler(w http.ResponseWriter, r *http.Request) {
	belongServiceURL := getEnv("BELONG_SERVICE_URL", "http://localhost:8000")
	authServiceURL := getEnv("AUTH_SERVICE_URL", "http://localhost:9001")

	belongStatus, belongMsg := checkService(belongServiceURL+"/healthz", 2*time.Second)
	authStatus, authMsg := checkService(authServiceURL+"/healthz", 2*time.Second)

	overallStatus := "ok"
	if belongStatus != "up" || authStatus != "up" {
		overallStatus = "degraded"
	}

	response := HealthResponse{
		Status: overallStatus,
		Services: []ServiceStatus{
			{Name: "belong-api", Status: belongStatus, Message: belongMsg},
			{Name: "auth-service", Status: authStatus, Message: authMsg},
		},
	}

	w.Header().Set("Content-Type", "application/json")
	if overallStatus == "ok" {
		w.WriteHeader(http.StatusOK)
	} else {
		w.WriteHeader(http.StatusServiceUnavailable)
	}
	json.NewEncoder(w).Encode(response)
}
