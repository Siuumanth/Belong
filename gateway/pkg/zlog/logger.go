package zlog

import (
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

// L is the global Zap Logger
var L *zap.Logger

func Init() {
	// NewDevelopment is great for dev; use NewProduction() for JSON
	config := zap.NewDevelopmentConfig()
	config.EncoderConfig.EncodeTime = zapcore.TimeEncoderOfLayout("2006-01-02 15:04:05")
	logger, _ := config.Build()
	L = logger
}

// Sync flushes any buffered log entries (call this in main)
func Sync() error {
	return L.Sync()
}
