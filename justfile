_default:
  -just --list --unsorted

fetch:
  uv run src/fetch_primuss.py

extract:
  uv run src/extract_instance.py

solve semester:
  uv run src/solve.py --semester {{semester}}

notebook:
  uv run marimo edit src/main.py

test:
  uv run pytest
