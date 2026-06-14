GO 	:= go
LINT	:= golangci-lint
TIMEOUT	:= 5m

TARGET_MODULES := services/discoverer services/scraper services/fetcher services/ocr sercices/processor services/api

.PHONY: all
all: lint test build

.PHONY: verify-toolchain
verify-toolchain:
	@echo "Checking dev requirements..."
	@command -v $(GO) >/dev/null 2>&1 || { echo "Go binary not found"; exit 1; }
	@command -v $(LINT) >/dev/null 2>&1 || { echo "Golangci-lint binary not found"; exit 1; }

.PHONY: lint
lint: verify-toolchain
	@echo "==> Executing global static analysis..."
	$(LINT) run ./...

.PHONY: test
test: verify-toolchain
	@echo "==> Running module test suites concurrently..."
	@set -e; for mod in $(TARGET_MODULES); do \
		echo "Executing tests in: $$mod"; \
		(cd $$mod && $(GO) test -v -race -timeout=$(TIMEOUT) ./...); \
	done

.PHONY: tidy
tidy:
	@echo "==> Aligning module dependencies..."
	@set -e; for mod in $(TARGET_MODULES); do \
		(cd $$mod && $(GO) mod tidy); \
	done

.PHONY: build
build:
	@echo "==> Compiling module targets..."
	@set -e; for mod in $(TARGET_MODULES); do \
		BIN_NAME=$$(basename $$mod); \
		echo "Compiling: $$mod --> ./bin/$$BIN_NAME"; \
		(cd $$mod && CGO_ENABLED=0 $(GO) build -ldflags="-w -s" -o ./bin/$$BIN_NAME ./cmd/...); \
	done

.PHONY: clean
clean:
	@echo "==> Removing compilation artifacts..."
	@set -e; for mod in $(TARGET_MODULES); do \
		rm -rf $$mod/bin; \
	done
