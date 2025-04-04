.PHONY: venv
venv:
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	@echo "venv is initialized"

.PHONY: apidoc
apidoc: venv
	. venv/bin/activate && pip install --requirement docs/source/requirements.txt
	. venv/bin/activate && cd docs && sphinx-apidoc -o source --force ../pumaguard

.PHONY: docs
docs: venv
	@echo "building documentation webpage"
	. venv/bin/activate && pip install --requirement docs/source/requirements.txt
	. venv/bin/activate && cd docs && sphinx-apidoc --output-dir source --force ../pumaguard
	git ls-files --exclude-standard --others
	git ls-files --exclude-standard --others | wc -l | grep "^0" --quiet
	git diff
	git diff --shortstat | wc -l | grep "^0" --quiet
	. venv/bin/activate && sphinx-build --builder html --fail-on-warning docs/source docs/build
	. venv/bin/activate && sphinx-build --builder linkcheck --fail-on-warning docs/source docs/build

.PHONY: install
install:
	poetry install

.PHONY: install-dev
install-dev:
	poetry install --only dev

.PHONY: install-ansible
install-ansible:
	poetry install --only ansible

.PHONY: test
test: install
	poetry run pytest --verbose --cov=pumaguard --cov-report=term-missing

.PHONY: build
build:
	poetry build

.PHONY: lint
lint: install pylint isort mypy bashate ansible-lint

.PHONY: pylint
pylint: install
	poetry run pylint --verbose --recursive=true --rcfile=pylintrc pumaguard tests scripts

.PHONY: isort
isort: install-dev
	poetry run isort pumaguard tests scripts

.PHONY: mypy
mypy: install
	poetry run mypy --install-types --non-interactive --check-untyped-defs pumaguard

.PHONY: bashate
bashate: install-dev
	poetry run bashate -v scripts/*sh pumaguard/completions/*sh

.PHONY: lint-notebooks
lint-notebooks: install-dev
	poetry run pynblint notebooks

.PHONY: ansible-lint
ansible-lint: install-dev
	poetry run ansible-lint -vv scripts

.PHONY: snap
snap:
	snapcraft

FUNCTIONAL_FILES = \
    "data/Stables/lion/SYFW2061.JPG" \
    "data/Stables/lion/SYFW0270.JPG"

.PHONY: run-functional
run-functional:
	@echo "running functional test"
	$(EXE) classify --settings models/model_settings_6_pre-trained_512_512.yaml $(FUNCTIONAL_FILES) 2>&1 | tee functional-test.output

.PHONY: check-functional
check-functional:
	if [ "$$(sed --quiet --regexp-extended '/^Predicted.*2061/s/^.*:\s*([0-9.%]+).*$$/\1/p' functional-test.output)" != '28.80%' ]; then \
		cat functional-test.output; \
		false; \
	fi; \
	if [ "$$(sed --quiet --regexp-extended '/^Predicted.*270.JPG/s/^.*:\s*([0-9.%]+).*$$/\1/p' functional-test.output)" != '64.72%' ]; then \
		cat functional-test.output; \
		false; \
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

.PHONY: configure-pi-zero
configure-pi-zero: install-dev
	poetry run ansible-playbook --inventory pi-zero, --ask-become-pass scripts/configure-pi.yaml

.PHONY: configure-pi-5
configure-pi-5: install-dev
	poetry run ansible-playbook --inventory pi-5, --ask-become-pass scripts/configure-pi.yaml

.PHONY: verify-poetry
verify-poetry: install
	$(MAKE) EXE="poetry run pumaguard" verify

.PHONY: verify-snap
verify-snap:
	$(MAKE) EXE="pumaguard" verify

.PHONY: verify
verify:
	$(EXE) verify --settings models/model_settings_6_pre-trained_512_512.yaml --verification-path data/verification 2>&1 | tee verify.output
	if [ "$$(awk '/^accuracy/ {print $$3}' verify.output)" != 92.75% ]; then false; fi

.PHONY: train
train:
	pumaguard train --epochs 1 --model-output . --lion data/Stables/lion --no-lion data/Stables/no-lion/ --no-load-previous-session

.PHONY: pre-commit
pre-commit: lint docs
	sed --in-place --regexp-extended 's/^python.*=.*/python = ">=3.10,<3.11"/' pyproject.toml
	poetry add 'tensorflow==2.15'
	poetry install
	$(MAKE) test
	# poetry run pip install tensorflow~=2.17.0
	# $(MAKE) test
	# poetry run pip install tensorflow~=2.18.0
	# $(MAKE) test
