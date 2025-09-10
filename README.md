# LangGraph Multi-Agent - Market Research Pipeline

## Overview
This project implements a multi-agent market research pipeline using LangGraph. It performs web search, extracts and analyzes facts, generates structured market research reports, and produces PDF outputs. The system uses Guardrails for prompt hardening, schema validation, and policy checks to ensure high-quality, safe outputs.

## Key Features

### Agents
- **ResearcherAgent**: Performs web search using SerpAPI, retrieves top 10 results, and fetches full page content for richer context.
- **AnalystAgent**: Extracts and cleans facts from search results, prioritizing those with full content.
- **WriterAgent**: Generates comprehensive market research reports in JSON format using Groq LLM, ensuring facts are structured objects with source, url, excerpt, and content.
- **NarrativeWriterAgent**: Converts structured reports into well-written market research articles.
- **ReviewerAgent**: Validates report schema, checks for policy violations, and generates PDF reports.

### Guardrails
- Prompt hardening to avoid hallucinations and enforce JSON output.
- Pydantic schema validation for final reports.
- Toxicity and policy violation checks.
- Circuit breaker to handle repeated failures gracefully.

### Data Sources
- Uses SerpAPI for Google web search.
- Fetches full page content with BeautifulSoup for detailed analysis.

### Observability
- Logs traces and run summaries to artifacts.
- Caches Groq API calls to reduce costs.

## Installation
Install dependencies:
```
pip install -r requirements.txt
```

## Usage
Run the main graph:
```
python -m src.graph
```
Enter your market research query when prompted. The system will output a JSON report and generate a PDF file.

## Notes
- Some sites may block automated requests or have SSL issues; warnings are logged but processing continues.
- Facts are limited in length to manage token budgets.
- PDF reports are saved with filenames based on the query.
