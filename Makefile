LAPTOP ?= laptop
DEVICE ?= pi-5
DEVICE_USER ?= pumaguard

.PHONY: apidoc
apidoc: poetry
	poetry run pip install --requirement docs/source/requirements.txt
	cd docs && poetry run sphinx-apidoc -o source --force ../pumaguard

.PHONY: docs
docs: poetry
	@echo "building documentation webpage"
	poetry run pip install --requirement docs/source/requirements.txt
	cd docs && poetry run sphinx-apidoc --output-dir source --force ../pumaguard
	git ls-files --exclude-standard --others
	git ls-files --exclude-standard --others | wc -l | grep "^0" --quiet
	git diff
	git diff --shortstat | wc -l | grep "^0" --quiet
	poetry run sphinx-build --builder html --fail-on-warning docs/source docs/build
	poetry run sphinx-build --builder linkcheck --fail-on-warning docs/source docs/build

.PHONY: assemble
assemble:
	if [ -f pumaguard-models/Makefile ]; then \
		$(MAKE) -C pumaguard-models; \
	fi

.PHONY: lock
lock: poetry
	poetry lock

.PHONY: update
update: poetry
	poetry update

# This version should match the base of the snap.
# core24 uses poetry-1.8. Later versions of poetry use a different lockfile format
# which is incompatible with older versions, leading to build failures in snapcraft.
.PHONY: poetry
poetry:
	pip install --upgrade pip
	pip install poetry~=1.8

.PHONY: install
install: assemble poetry
	poetry install

.PHONY: install-dev
install-dev: poetry
	poetry install --only dev

.PHONY: test
test: install
	poetry run pytest --verbose --cov=pumaguard --cov-report=term-missing

.PHONY: build
build: assemble poetry
	poetry build

.PHONY: lint
lint: black pylint isort mypy bashate ansible-lint

.PHONY: black
black: install-dev
	poetry run black --check pumaguard

.PHONY: pylint
pylint: install
	poetry run pylint --verbose --recursive=true --rcfile=pylintrc pumaguard tests scripts

.PHONY: isort
isort: install-dev
	poetry run isort pumaguard tests scripts

.PHONY: mypy
mypy: install-dev
	poetry run mypy --install-types --non-interactive --check-untyped-defs pumaguard

.PHONY: bashate
bashate: install-dev
	poetry run bashate -v -i E006 scripts/*sh pumaguard/completions/*sh

.PHONY: ansible-lint
ansible-lint: install-dev
	ANSIBLE_ASK_VAULT_PASS=true poetry run ansible-lint -v scripts/configure-device.yaml
	ANSIBLE_ASK_VAULT_PASS=true poetry run ansible-lint -v scripts/configure-laptop.yaml

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
	if [ "$$(sed --quiet --regexp-extended '/^Predicted.*lion\.5/s/^.*:\s*([0-9.%]+).*$$/\1/p' functional-test.output)" != '99.10%' ]; then \
		cat functional-test.output; \
		exit 1; \
	fi; \
	if [ "$$(sed --quiet --regexp-extended '/^Predicted.*lion\.10/s/^.*:\s*([0-9.%]+).*$$/\1/p' functional-test.output)" != '90.56%' ]; then \
		cat functional-test.output; \
		exit 1; \
	fi; \
	if [ "$$(sed --quiet --regexp-extended '/^Predicted.*lion\.15/s/^.*:\s*([0-9.%]+).*$$/\1/p' functional-test.output)" != '98.25%' ]; then \
		cat functional-test.output; \
		exit 1; \
	fi; \
	if [ "$$(sed --quiet --regexp-extended '/^Predicted.*other\.2/s/^.*:\s*([0-9.%]+).*$$/\1/p' functional-test.output)" != '0.00%' ]; then \
		cat functional-test.output; \
		exit 1; \
	fi; \
	if [ "$$(sed --quiet --regexp-extended '/^Predicted.*other\.7/s/^.*:\s*([0-9.%]+).*$$/\1/p' functional-test.output)" != '32.73%' ]; then \
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
	$(MAKE) EXE="poetry run pumaguard" run-functional
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
	poetry run ansible-playbook --inventory $(DEVICE), --user $(DEVICE_USER) --diff --ask-become-pass --ask-vault-pass scripts/configure-device.yaml

.PHONY: configure-laptop
configure-laptop: install-dev
	poetry run ansible-playbook --inventory $(LAPTOP), --diff --ask-become-pass --ask-vault-pass scripts/configure-laptop.yaml

.PHONY: verify-poetry
verify-poetry: install
	$(MAKE) EXE="poetry run pumaguard" verify

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
pre-commit: lint docs poetry
	sed --in-place --regexp-extended 's/^python.*=.*/python = ">=3.10,<3.11"/' pyproject.toml
	poetry add 'tensorflow==2.15'
	poetry install
	$(MAKE) test
	# poetry run pip install tensorflow~=2.17.0
	# $(MAKE) test
	# poetry run pip install tensorflow~=2.18.0
	# $(MAKE) test
