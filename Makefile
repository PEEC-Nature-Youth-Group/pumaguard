LAPTOP ?= laptop
DEVICE ?= pi-5
DEVICE_USER ?= pumaguard
ANSIBLE_ASK_VAULT_PASS ?= true
ANSIBLE_VAULT_PASSWORD_FILE ?=
NEW_MODEL ?=

.venv:
	uv venv
	uv pip install --upgrade pip

.PHONY: apidoc
apidoc: .venv
	uv sync --extra docs --frozen
	. .venv/bin/activate && cd docs && sphinx-apidoc -o source --force ../pumaguard

.PHONY: docs
docs: .venv
	@echo "building documentation webpage"
	uv sync --extra docs --frozen
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
	uv pip install --editable .

.PHONY: install-dev
install-dev: .venv
	uv sync --extra dev --frozen

.PHONY: test
test: install-dev
	uv run --frozen pytest --verbose --cov=pumaguard --cov-report=term-missing

.PHONY: test-ui
test-ui:
	cd pumaguard-ui; flutter pub get
	cd pumaguard-ui; dart format --set-exit-if-changed lib test
	cd pumaguard-ui; flutter analyze
	cd pumaguard-ui; flutter test

.PHONY: build
build: install-dev build-ui
	uv build

.PHONY: lint
lint: black pylint isort mypy bashate

.PHONY: black
black: install-dev
	uv run --frozen black --check pumaguard

.PHONY: pylint
pylint: install-dev
	uv run --frozen pylint --verbose --recursive=true --rcfile=pylintrc pumaguard tests scripts

.PHONY: isort
isort: install-dev
	uv run --frozen isort pumaguard tests scripts

.PHONY: mypy
mypy: install-dev
	. .venv/bin/activate && mypy --install-types --non-interactive --check-untyped-defs pumaguard

.PHONY: bashate
bashate: install-dev
	uv run --frozen bashate -v -i E006 scripts/*sh pumaguard/completions/*sh

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

.PHONY: functional-poetry
functional-poetry: install
	$(MAKE) EXE="uv run pumaguard" run-functional
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
configure-device: install-dev
	$(VENV)ansible-playbook --inventory $(DEVICE), --user $(DEVICE_USER) --diff --ask-become-pass --ask-vault-pass scripts/configure-device.yaml

.PHONY: configure-laptop
configure-laptop: install-dev
	$(VENV)ansible-playbook --inventory $(LAPTOP), --diff --ask-become-pass --ask-vault-pass scripts/configure-laptop.yaml

.PHONY: verify-poetry
verify-poetry: install
	$(MAKE) EXE="uv run --frozen pumaguard" verify

.PHONY: verify-snap
verify-snap:
	$(MAKE) EXE="pumaguard" verify

.PHONY: verify
verify:
	$(EXE) verify --debug --settings pumaguard-models/model_settings_6_pre-trained_512_512.yaml --verification-path training-data/verification 2>&1 | tee verify.output
	if [ "$$(awk '/^accuracy/ {print $$3}' verify.output)" != 92.75% ]; then echo "ignoring"; fi

.PHONY: train
train:
	pumaguard train --debug --epochs 1 --model-output . --lion training-data/Stables/lion --no-lion training-data/Stables/no-lion/ --no-load-previous-session

.PHONY: test-server
test-server: install
	./scripts/test-server.sh

.PHONY: pre-commit
pre-commit: lint docs poetry test-ui
	$(MAKE) test

.PHONY: add-model
add-model:
	if [ -z "$(NEW_MODEL)" ]; then false; fi
	cd pumaguard-models; sha256sum $(NEW_MODEL)_* | while read checksum fragment; do \
        yq --inplace ".\"$(NEW_MODEL)\".fragments.\"$${fragment}\".sha256sum = \"$${checksum}\"" ../pumaguard/model-registry.yaml; \
    done

.PHONY: build-ui
build-ui: install
	cd pumaguard-ui; flutter pub get
	cd pumaguard-ui; flutter build web --wasm
	mkdir -p pumaguard/pumaguard-ui
	rsync -av --delete pumaguard-ui/build/web/ pumaguard/pumaguard-ui/

.PHONY: run-server
run-server: install build-ui
	uv run --frozen pumaguard server

.PHONY: server-container-test
server-container-test:
	if [ -n $$(lxc list --format json | jq --raw-output '.[] | select(.name == "pumaguard") | .name') ]; then lxc delete --force pumaguard; fi
	lxc init ubuntu:noble pumaguard
	[ -d dist ] && gio trash dist || echo "no dist, ignoring"
	$(MAKE) build
	lxc config device add pumaguard dist disk source=$${PWD}/dist path=/dist
	printf "uid 1000 $$(id --user)\ngid 1000 $$(id --group)" | lxc config set pumaguard raw.idmap -
	lxc start pumaguard
	lxc exec pumaguard -- cloud-init status --wait
	lxc exec pumaguard -- apt-get update
	lxc exec pumaguard -- apt-get install --no-install-recommends --yes pipx
	lxc exec pumaguard -- sudo --user ubuntu --login pipx install --verbose --pip-args="--verbose" /$$(ls dist/*whl)
	lxc exec pumaguard -- sudo --user ubuntu --login pipx ensurepath
	lxc exec pumaguard -- sudo --user ubuntu --login pumaguard server --debug
