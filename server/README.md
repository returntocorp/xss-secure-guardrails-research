# XSS Research Triage Server

This is a simple triage server built for making manual review of commit diffs + Semgrep results a bit easier.

## Running the server

This server is built with Flask. Dependencies are managed with Poetry. To run the server, do these things:

1. Install dependencies with Poetry: `poetry install`
1. Activate the Poetry environment: `poetry shell`
1. Run the server. From this `server/` directory: `python xss_research/app.py`
1. If you want to select a different database, use an environment variable: `RULE_STATS_DB=some_other_db.db python xss_research/app.py`

ezpz!~