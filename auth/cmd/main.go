package main

import (
	"auth/internal/dao/postgres"
	"auth/internal/database"
	"auth/internal/handler"
	"auth/internal/router"
	"auth/internal/service"
	"fmt"
	"net/http"
	"os"

	"github.com/joho/godotenv"
)

func main() {
	_ = godotenv.Load(".env")
	_ = godotenv.Load("../.env")

	fmt.Println("=========================================")
	fmt.Println("       Starting Belong Auth Service       ")
	fmt.Println("=========================================")

	dbURL := os.Getenv("AUTH_POSTGRES_URL_DEV")
	if dbURL == "" {
		dbURL = "postgres://belong_user:belong_password@localhost:5432/belong?sslmode=disable"
	}

	db, err := database.Connect(dbURL)
	if err != nil {
		fmt.Printf("[ERROR] DB Connection Failed: %v\n", err)
		panic(err)
	}
	fmt.Println("[OK] Connected to PostgreSQL Database.")

	port := os.Getenv("PORT")
	if port == "" {
		port = "9001"
	}

	authDao := postgres.NewPostgresUserDAO(db)
	authService := service.NewAuthService(authDao)
	authHandler := handler.NewAuthHandler(authService)
	userRouter := router.NewRouter(authHandler)

	fmt.Printf("[OK] Belong Auth Service is READY and listening on port :%s\n", port)
	err = http.ListenAndServe(":"+port, userRouter)
	if err != nil {
		fmt.Printf("[ERROR] Failed to start Auth server: %v\n", err)
		panic(err)
	}
}
