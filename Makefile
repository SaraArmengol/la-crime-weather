.PHONY: install data pipeline test lint app clean

install:
	pip install -e ".[app,dev]"

data:            ## Download raw crime, weather, and scraped data
	crime-weather extract

pipeline:        ## Run the full pipeline: extract -> transform -> load -> model -> publish
	crime-weather all

test:
	pytest -q

lint:
	ruff check src tests app

app:
	streamlit run app/streamlit_app.py

clean:
	rm -rf data/interim/* data/processed/* data/warehouse.duckdb
