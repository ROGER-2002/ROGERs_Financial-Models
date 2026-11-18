# Contributing

1. Create a branch from `main`, such as `feature/holdings-risk` or `fix/drawdown-start-point`.
2. Keep each pull request focused and explain the investment/business behavior it changes.
3. Add or update tests for calculation and data-contract changes. Never commit real client, fund, vendor, or licensed data.
4. Run `ruff check .` and `pytest` before opening a pull request.
5. Request review from a code owner and, for financial logic, an investment/risk reviewer.
6. Merge only after required checks and reviews pass. Production releases require the agreed release approval process.

Never commit credentials, `.streamlit/secrets.toml`, private report exports, or source datasets. Use synthetic fixtures for development and tests.
