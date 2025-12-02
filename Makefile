.PHONY: pre-commit
pre-commit: analyze format build

.PHONY: analyze
analyze:
	flutter analyze

.PHONY: format
format:
	dart format lib

.PHONY: build
build:
	flutter build web --wasm
