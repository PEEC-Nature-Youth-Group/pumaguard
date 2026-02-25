# Ansible configuration variables:
# - ANSIBLE_TAGS: Run only specific tags (e.g., ANSIBLE_TAGS=network,users)
# - ANSIBLE_SKIP_TAGS: Skip specific tags (e.g., ANSIBLE_SKIP_TAGS=pumaguard)
# - If both are empty, all tasks run
# - ANSIBLE_TAGS takes precedence if both are set
#
# Examples:
#   make configure-device                              # Run all tasks
#   make configure-device ANSIBLE_SKIP_TAGS=pumaguard  # Skip pumaguard tag
#   make configure-device ANSIBLE_TAGS=network         # Run only network tag
#   make configure-device ANSIBLE_TAGS=users,ssh       # Run users and ssh tags
LAPTOP ?= laptop
DEVICE ?= pi-5
DEVICE_USER ?= pumaguard
ANSIBLE_ASK_VAULT_PASS ?= true
ANSIBLE_VAULT_PASSWORD_FILE ?=
ANSIBLE_SKIP_TAGS ?=
ANSIBLE_TAGS ?=
NEW_MODEL ?=
TEST_NAME ?= pumaguard-test

.venv:
	uv venv
	uv pip install --native-tls --upgrade pip

.PHONY: apidoc
apidoc: .venv
	uv sync --extra docs --frozen
	. .venv/bin/activate && cd docs && sphinx-apidoc -o source --force ../pumaguard

.PHONY: docs
docs: .venv
	@echo "building documentation webpage"
	uv sync --native-tls --extra docs --frozen
	. .venv/bin/activate && cd docs && sphinx-apidoc --output-dir source --force ../pumaguard
	git ls-files --exclude-standard --others
	git ls-files --exclude-standard --others | wc -l | grep "^0" --quiet
	git diff
	git diff --shortstat | wc -l | grep "^0" --quiet
	. .venv/bin/activate && sphinx-build --builder html --fail-on-warning docs/source docs/build
	. .venv/bin/activate && sphinx-build --builder linkcheck --fail-on-warning docs/source docs/build

.PHONY: assemble
assemble:
	if [ -f pumaguard-models/Makefile ]; then \
		$(MAKE) -C pumaguard-models; \
	fi

.PHONY: install
install: assemble .venv
	uv pip install --native-tls --editable .

.PHONY: install-dev
install-dev: .venv
	uv sync --native-tls --extra dev --frozen

.PHONY: test
test: test-python test-ui

.PHONY: test-python
test-python: install-dev
	timeout 300 uv run --native-tls --frozen pytest --verbose --cov=pumaguard --cov-report=term-missing

.PHONY: lint-ui
lint-ui:
	make -C pumaguard-ui version
	cd pumaguard-ui; flutter pub get
	cd pumaguard-ui; dart format --set-exit-if-changed lib test
	cd pumaguard-ui; flutter analyze

.PHONY: test-ui
test-ui:
	make -C pumaguard-ui version
	cd pumaguard-ui; flutter pub get
	cd pumaguard-ui; flutter test

.PHONY: build
build: install build-ui
	uv build

.PHONY: lint
lint: black pylint isort mypy bashate
	@echo "done linting"

.PHONY: black
black: install-dev
	uv run --native-tls --frozen black --check pumaguard

.PHONY: pylint
pylint: install-dev
	uv run --native-tls --frozen pylint --verbose --recursive=true --rcfile=pylintrc pumaguard tests scripts

.PHONY: isort
isort: install-dev
	uv run --native-tls --frozen isort pumaguard tests scripts

.PHONY: mypy
mypy: install-dev
	. .venv/bin/activate && mypy --install-types --non-interactive --check-untyped-defs pumaguard

.PHONY: bashate
bashate: install-dev
	uv run --native-tls --frozen bashate -v -i E006 scripts/*sh pumaguard/completions/*sh

.PHONY: ansible-lint
ansible-lint: install-dev
	ANSIBLE_ASK_VAULT_PASS=$(ANSIBLE_ASK_VAULT_PASS) ANSIBLE_VAULT_PASSWORD_FILE=$(ANSIBLE_VAULT_PASSWORD_FILE) uv run --frozen ansible-lint -v scripts/configure-device.yaml
	ANSIBLE_ASK_VAULT_PASS=$(ANSIBLE_ASK_VAULT_PASS) ANSIBLE_VAULT_PASSWORD_FILE=$(ANSIBLE_VAULT_PASSWORD_FILE) uv run --frozen ansible-lint -v scripts/configure-laptop.yaml

.PHONY: snap
snap:
	snapcraft

FUNCTIONAL_FILES = \
    "training-data/testlion_100525/lion.5.jpg" \
    "training-data/testlion_100525/lion.10.jpg" \
    "training-data/testlion_100525/lion.15.jpg" \
    "training-data/testlion_100525/other.2.jpg" \
    "training-data/testlion_100525/other.7.jpg" \
    "training-data/testlion_100525/other.17.jpg"

.PHONY: run-functional
run-functional:
	@echo "running functional test"
	$(EXE) classify --debug $(FUNCTIONAL_FILES) 2>&1 | tee functional-test.output

.PHONY: check-functional
check-functional:
	if [ "$$(sed --quiet --regexp-extended '/^Predicted.*lion\.5/s/^.*:\s*([0-9.%]+).*$$/\1/p' functional-test.output)" != '99.92%' ]; then \
		cat functional-test.output; \
		exit 1; \
	fi; \
	if [ "$$(sed --quiet --regexp-extended '/^Predicted.*lion\.10/s/^.*:\s*([0-9.%]+).*$$/\1/p' functional-test.output)" != '99.99%' ]; then \
		cat functional-test.output; \
		exit 1; \
	fi; \
	if [ "$$(sed --quiet --regexp-extended '/^Predicted.*lion\.15/s/^.*:\s*([0-9.%]+).*$$/\1/p' functional-test.output)" != '99.99%' ]; then \
		cat functional-test.output; \
		exit 1; \
	fi; \
	if [ "$$(sed --quiet --regexp-extended '/^Predicted.*other\.2/s/^.*:\s*([0-9.%]+).*$$/\1/p' functional-test.output)" != '0.00%' ]; then \
		cat functional-test.output; \
		exit 1; \
	fi; \
	if [ "$$(sed --quiet --regexp-extended '/^Predicted.*other\.7/s/^.*:\s*([0-9.%]+).*$$/\1/p' functional-test.output)" != '0.00%' ]; then \
		cat functional-test.output; \
		exit 1; \
	fi; \
	if [ "$$(sed --quiet --regexp-extended '/^Predicted.*other\.17/s/^.*:\s*([0-9.%]+).*$$/\1/p' functional-test.output)" != '0.00%' ]; then \
		cat functional-test.output; \
		exit 1; \
	fi
	@echo "Success"

.PHONY: functional-python
functional-python: install
	$(MAKE) EXE="uv run --native-tls pumaguard" run-functional
	$(MAKE) check-functional

.PHONY: functional-snap
functional-snap:
	$(MAKE) EXE="pumaguard" run-functional
	$(MAKE) check-functional

.PHONY: prepare-trailcam prepare-output prepare-central
prepare-central prepare-trailcam prepare-output: prepare-%:
	scripts/launch-pi-zero.sh --name $* --force
	multipass transfer pumaguard_$(shell git describe --tags)*.snap $*:/home/ubuntu
	multipass exec $* -- sudo snap install --dangerous --devmode $(shell ls pumaguard*snap)

.PHONY: release
release:
	export NEW_RELEASE=$(shell git tag | sed --expression 's/^v//' | \
	    sort --numeric-sort | tail --lines 1 | awk '{print $$1 + 1}') && \
	  git tag -a -m "Release v$${NEW_RELEASE}" v$${NEW_RELEASE}

.PHONY: configure-device
configure-device: install-dev build
	@ANSIBLE_CMD="ANSIBLE_CALLBACK_RESULT_FORMAT=yaml uv run ansible-playbook --inventory $(DEVICE), --user $(DEVICE_USER) --diff --ask-become-pass --ask-vault-pass --extra-vars \"pumaguard_install_method=local\""; \
	if [ -n "$(ANSIBLE_TAGS)" ]; then \
		ANSIBLE_CMD="$$ANSIBLE_CMD --tags $(ANSIBLE_TAGS)"; \
	fi; \
	if [ -n "$(ANSIBLE_SKIP_TAGS)" ]; then \
		ANSIBLE_CMD="$$ANSIBLE_CMD --skip-tags $(ANSIBLE_SKIP_TAGS)"; \
	fi; \
	ANSIBLE_CMD="$$ANSIBLE_CMD scripts/configure-device.yaml"; \
	eval $$ANSIBLE_CMD

.PHONY: configure-laptop
configure-laptop: install-dev
	@ANSIBLE_CMD="uv run ansible-playbook --inventory $(LAPTOP), --diff --ask-become-pass --ask-vault-pass"; \
	if [ -n "$(ANSIBLE_TAGS)" ]; then \
		ANSIBLE_CMD="$$ANSIBLE_CMD --tags $(ANSIBLE_TAGS)"; \
	fi; \
	if [ -n "$(ANSIBLE_SKIP_TAGS)" ]; then \
		ANSIBLE_CMD="$$ANSIBLE_CMD --skip-tags $(ANSIBLE_SKIP_TAGS)"; \
	fi; \
	ANSIBLE_CMD="$$ANSIBLE_CMD scripts/configure-laptop.yaml"; \
	eval $$ANSIBLE_CMD

.PHONY: verify-poetry
verify-poetry: install
	$(MAKE) EXE="uv run --native-tls --frozen pumaguard" verify

.PHONY: verify-snap
verify-snap:
	$(MAKE) EXE="pumaguard" verify

.PHONY: verify
verify:
	$(EXE) verify --debug --settings pumaguard-models/model_settings_6_pre-trained_512_512.yaml --verification-path training-data/verification 2>&1 | tee verify.output
	if [ "$$(awk '/^accuracy/ {print $$3}' verify.output)" != 92.75% ]; then echo "ignoring"; fi

.PHONY: test-server
test-server: install
	./scripts/test-server.sh

.PHONY: pre-commit
pre-commit: docs lint test

.PHONY: add-model
add-model:
	if [ -z "$(NEW_MODEL)" ]; then false; fi
	cd pumaguard-models; sha256sum $(NEW_MODEL)_* | while read checksum fragment; do \
        yq --inplace ".\"$(NEW_MODEL)\".fragments.\"$${fragment}\".sha256sum = \"$${checksum}\"" ../pumaguard/model-registry.yaml; \
    done

.PHONY: build-ui
build-ui: install
	make -C pumaguard-ui version
	cd pumaguard-ui; flutter pub get
	cd pumaguard-ui; flutter build web --release --no-web-resources-cdn --pwa-strategy=none --wasm
	mkdir --parents pumaguard/pumaguard-ui
	rsync -av --delete pumaguard-ui/build/web/ pumaguard/pumaguard-ui/

.PHONY: run-server
run-server: install build-ui
	uv run --native-tls --frozen pumaguard server

.PHONY: dev-backend
dev-backend: build install
	@echo "Starting PumaGuard backend in debug mode..."
	uv run --native-tls --frozen pumaguard server --debug

API_BASE_URL ?= http://localhost:5000

.PHONY: dev-ui-web
dev-ui-web:
	@echo "Starting Flutter web dev server (run 'make dev-backend' in another terminal)..."
	$(MAKE) -C pumaguard-ui dev-ui-web API_BASE_URL=$(API_BASE_URL)

.PHONY: server-container-test
server-container-test:
	@if lxc info $(TEST_NAME) >/dev/null 2>&1; then \
		echo "Container $(TEST_NAME) exists, updating..."; \
	else \
		echo "Container $(TEST_NAME) does not exist, creating..."; \
		lxc init --vm ubuntu:noble $(TEST_NAME); \
	fi
	$(MAKE) server-container-update

.PHONY: server-container-update
server-container-update:
	lxc stop $(TEST_NAME) || echo "ignoring"
	[ -d dist ] && gio trash dist || echo "no dist, ignoring"
	$(MAKE) build
	[ -d wheelhouse ] && gio trash wheelhouse || echo "no wheelhouse, ignoring"
	mkdir --parents wheelhouse
	. .venv/bin/activate && python -m pip download --dest wheelhouse $$(ls dist/*.whl)
	[ -d watch ] && gio trash watch || echo "no watch folder, ignoring"
	mkdir --parents watch
	lxc config device show $(TEST_NAME) | grep -q "^dist:" || \
		lxc config device add $(TEST_NAME) dist disk source=$${PWD}/dist path=/dist
	lxc config device show $(TEST_NAME) | grep -q "^wheelhouse:" || \
		lxc config device add $(TEST_NAME) wheelhouse disk source=$${PWD}/wheelhouse path=/wheelhouse
	lxc config device show $(TEST_NAME) | grep -q "^watch:" || \
		lxc config device add $(TEST_NAME) watch disk source=$${PWD}/watch path=/watch
	printf "uid 1000 $$(id --user)\ngid 1000 $$(id --group)" | lxc config set $(TEST_NAME) raw.idmap -
	lxc start $(TEST_NAME) 2>/dev/null || echo "Container already running"
	lxc exec $(TEST_NAME) -- cloud-init status --wait || echo "ignoring error"
	lxc exec $(TEST_NAME) -- apt-get update
	lxc exec $(TEST_NAME) -- apt-get install --no-install-recommends --yes pipx mpg123 libgl1
	lxc exec $(TEST_NAME) -- sudo --user ubuntu --login pipx upgrade \
		--verbose \
		--pip-args="--no-index --find-links=/wheelhouse --verbose" \
		pumaguard || \
	lxc exec $(TEST_NAME) -- sudo --user ubuntu --login pipx install \
		--force \
		--verbose \
		--pip-args="--no-index --find-links=/wheelhouse --verbose" \
		/$$(ls dist/*whl)
	lxc exec $(TEST_NAME) -- sudo --user ubuntu --login pipx ensurepath
	lxc exec $(TEST_NAME) -- sudo --user ubuntu --login pumaguard server --debug /watch

.PHONY: server-container-delete
server-container-delete:
	lxc delete --force $(TEST_NAME) || echo "no existing $(TEST_NAME) instance"
