# Repository Guidelines

## Project Structure & Module Organization

The repository follows a modular Python architecture for CS2 skin quantitative trading:


- **src/** - Core source code modules:
  - main.py - Entry point with real-time opportunity scanning
  - api_client.py - Market API clients (SteamDT, CSQAQ)
  - database.py - SQLite database operations
  - strategy.py - Quantitative trading strategy logic
  - backtest_*.py - Backtest engine components

- **config/** - Configuration management
  - config.py - Main application configuration
  - backtest_config.py - Backtest-specific settings

- **scripts/** - Utility and automation scripts
  - backtest_quick.py - Quick backtest execution
  - run_backtest.py - Complete backtest pipeline
  - auto_backtest.py - Automated scheduling

- **data/** - Static datasets and mappings
  - csqaq_id_map.json - Item name to ID mapping
  - steam_items_database.json - Reference database
  - low_sales_blacklist.txt - Excluded items

- **databases/** - SQLite database files (.db)
- **output/** - Generated results and logs
- **docs/** - Project documentation
- **tests/** - Unit tests (when implemented)

## Build, Test, and Development Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your API keys
```

### Development Execution
```bash
# Quick backtest
python scripts/backtest_quick.py quick

# Full backtest pipeline
python scripts/run_backtest.py

# Strategy weight optimization
python run_weight_optimization.py
```

### Docker Deployment
```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f
```

### GitHub Actions Automation
```bash
# Manual workflow trigger (if configured)
git push origin main
```

## Coding Style & Naming Conventions

- **Python**: PEP 8 compliance, 4-space indentation, snake_case for functions/variables
- **Imports**: Standard library -> third-party -> local modules, grouped with blank lines
- **Documentation**: Chinese/English docstrings for public methods, key English comments
- **Naming**: Descriptive names reflecting financial/trading context (e.g., calculate_sharpe_ratio)
- **Error handling**: Use try-except blocks with specific exception types, log meaningful errors
- **Configuration**: Store sensitive data in .env, reference via config.py

## Testing Guidelines

- **Framework**: unittest or pytest (to be implemented)
- **Coverage**: Focus on core business logic (strategy, database, API clients)
- **Test data**: Use data/ directory for fixtures, mock external API calls
- **Test structure**: Mirror src/ layout with test_ prefix (e.g., test_strategy.py)
- **Execution**: Run tests before committing significant changes

## Commit & Pull Request Guidelines

- **Commits**: Descriptive present-tense messages in Chinese/English
  - Example: feat: 添加新的回测可视化图表
  - Example: fix: 修复CSQAQ API令牌验证问题
- **Scope**: One logical change per commit; group related file modifications
- **PR requirements**:
  - Link to related issue/task
  - Describe changes and testing performed
  - Include screenshots for UI/visual changes
  - Ensure no breaking changes to existing functionality
  - Update documentation if APIs change

## Agent-Specific Instructions

- **Configuration**: Always check .env exists before running; use .env.example as template
- **Data persistence**: SQLite databases in databases/ auto-created; backup before major changes
- **API limits**: Respect rate limits for SteamDT and CSQAQ APIs; implement retry logic
- **Backtest results**: Output to output/backtest_results/ with timestamp folders
- **Logs**: Check logs/ and output/backtest_logs/ for debugging

---
*This document serves as the primary contributor guide for the CS2 Skin Quantitative Trading System repository.*
