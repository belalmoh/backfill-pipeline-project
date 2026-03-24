# Clickstream Analytics Pipeline - Makefile
# Useful commands for managing the environment

.PHONY: help start stop restart status logs clean build ps

PROFILE ?= core

# Default target
help:
	@echo "Clickstream Analytics Pipeline - Makefile Commands"
	@echo ""
	@echo "Usage: make [command]"
	@echo ""
	@echo "Commands:"
	@echo "  start      - Start Docker services for PROFILE (default: core)"
	@echo "  stop       - Stop all Docker services"
	@echo "  restart    - Restart all Docker services"
	@echo "  status     - Show status of all services"
	@echo "  logs       - Show logs (use LOGS=servicename for specific service)"
	@echo "  ps         - Same as status"
	@echo "  build      - Build and start services for PROFILE"
	@echo "  clean      - Stop and remove containers and volumes"
	@echo ""
	@echo "Examples:"
	@echo "  make start                   # Start core profile"
	@echo "  make start PROFILE=core,streaming"
	@echo "  make start PROFILE=core,orchestration,compute"
	@echo "  make start PROFILE=core,streaming,orchestration,compute"
	@echo "  make stop            # Stop all services"
	@echo "  make status          # Check service status"
	@echo "  make logs            # Show all logs"
	@echo "  make logs LOGS=postgres  # Show postgres logs"
	@echo "  make clean           # Clean start (removes volumes)"
	@echo ""
	@echo "Service URLs:"
	@echo "  Airflow:       http://localhost:8080"
	@echo "  MinIO Console: http://localhost:9001"
	@echo "  Spark Master:  http://localhost:8082"
	@echo ""

# Start all services
start:
	@echo "Starting Docker services for PROFILE=$(PROFILE)..."
	COMPOSE_PROFILES=$(PROFILE) docker compose up -d
	@echo ""
	@echo "Waiting for services to be healthy..."
	@sleep 30
	@COMPOSE_PROFILES=$(PROFILE) docker compose ps

# Stop all services
stop:
	@echo "Stopping all services..."
	COMPOSE_PROFILES=core,streaming,orchestration,compute docker compose down

# Restart all services
restart: stop start

# Show status of all services
status:
	COMPOSE_PROFILES=$(PROFILE) docker compose ps

# Alias for status
ps: status

# Show logs
logs:
ifdef LOGS
	COMPOSE_PROFILES=$(PROFILE) docker compose logs -f $(LOGS)
else
	COMPOSE_PROFILES=$(PROFILE) docker compose logs -f
endif

# Build and start
build:
	@echo "Building and starting Docker services for PROFILE=$(PROFILE)..."
	COMPOSE_PROFILES=$(PROFILE) docker compose up -d --build
	@echo ""
	@echo "Waiting for services to be healthy..."
	@sleep 30
	@COMPOSE_PROFILES=$(PROFILE) docker compose ps

# Clean - Remove containers and volumes
clean:
	@echo "WARNING: This will remove all data!"
	@echo "Stopping and removing containers and volumes..."
	docker compose down -v
	@echo "Cleanup complete."