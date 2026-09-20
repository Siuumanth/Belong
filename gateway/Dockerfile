# -------- BUILD STAGE --------
FROM golang:1.24-alpine AS builder

WORKDIR /app

ENV GOTOOLCHAIN=local

RUN apk add --no-cache git

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN go mod tidy
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -o gateway ./cmd

# -------- RUNTIME STAGE --------
FROM alpine:3.19

WORKDIR /app

RUN apk add --no-cache ca-certificates

COPY --from=builder /app/gateway ./gateway

EXPOSE 9000

ENV PORT=9000

ENTRYPOINT ["./gateway"]
