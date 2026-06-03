# ============================================================
#  fin — Selachii Package Manager
#  Selachii Project © 2026 — GPL v3
#  Makefile
# ============================================================
.PHONY: install dev build clean test lint

# ── Dev setup ────────────────────────────────────────────────
dev:
	pip install -e ".[dev]" --break-system-packages
	pip install requests zstandard python-gnupg pyinstaller pytest --break-system-packages

# ── Run directly ─────────────────────────────────────────────
run:
	python3 run_fin.py $(ARGS)

# ── Build binary via PyInstaller ─────────────────────────────
build:
	python3 -m PyInstaller fin.spec
	@echo ""
	@echo "Binary ready: dist/fin"

# ── Tests ────────────────────────────────────────────────────
test:
	pytest tests/ -v

# ── Lint ─────────────────────────────────────────────────────
lint:
	python3 -m py_compile fin/**/*.py && echo "No syntax errors"

# ── Clean ────────────────────────────────────────────────────
clean:
	rm -rf dist/ build/ __pycache__ \
		fin/__pycache__ fin/**/__pycache__

# ── Release (tag + push) ─────────────────────────────────────
release:
	@echo "Tagging v$(VERSION)..."
	git tag v$(VERSION)
	git push origin v$(VERSION)
