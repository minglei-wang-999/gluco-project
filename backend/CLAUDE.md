# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This is the **Gluco Backend** - a FastAPI-based web service providing nutritional analysis and glycemic impact assessment for food images. Part of the Gluco monorepo project, primarily designed for WeChat Mini Program integration (`../wx-client`) with dual authentication (email + WeChat users).

**Key Technologies:** FastAPI, SQLAlchemy, MySQL, OpenAI Vision API, WeChat integration, Docker

## Commands
**Note:** All commands should be run from the `backend/` directory within the monorepo.

- **Development:** `poetry run uvicorn app.main:app --reload`
- **Test all:** `poetry run pytest`
- **Test single file:** `poetry run pytest tests/test_file.py`
- **Test single test:** `poetry run pytest tests/test_file.py::TestClass::test_function`
- **Coverage:** `poetry run pytest --cov=app tests/`
- **Migration current:** `poetry run alembic current`
- **Migration upgrade:** `poetry run alembic upgrade head`
- **Add dependency:** `poetry add package_name`
- **Install dependencies:** `poetry install`

## Architecture Overview

**Core Structure:**
- `app/routers/` - API endpoints (auth, meals, users, weixin, subscription)
- `app/models/` - SQLAlchemy models (User, WeixinUser, NutritionRecord, Ingredient, Subscription)
- `app/schemas/` - Pydantic validation schemas
- `app/services/` - Business logic (payment, subscription management)
- `app/utils/` - Utilities (auth, GPT client, email, timezone handling)
- `app/storage/` - WeChat cloud storage integration
- `alembic/` - Database migrations

**Dual User System:**
- Email-based users (`User` model) with JWT authentication
- WeChat users (`WeixinUser` model) with OpenID-based auth
- Both can access core nutritional analysis features

**Database Design:**
- MySQL with timezone-aware timestamps throughout
- Comprehensive migration history (17+ migrations)
- Test database isolation for each test

## Development Workflow
1. **Update tests first** (TDD approach)
2. **Implement code** to pass tests
3. **Run migrations** if schema changes needed
4. **Always run tests** before committing
5. Use test classes instead of individual test functions

## Key Integration Points

**OpenAI Integration:**
- Food image analysis via Vision API
- Nutritional calculation prompts in `app/utils/gpt_client.py`
- Mock responses in tests to avoid API costs

**WeChat Mini Program Integration:**
- Frontend client located at `../wx-client/`
- Authentication via OpenID in `app/routers/weixin_auth.py`
- Cloud storage for image uploads in `app/storage/`
- Payment processing with certificates in `certs/`
- Frontend API calls defined in `../wx-client/utils/api.js`

**Database Patterns:**
- Always use Alembic for schema changes
- Timezone-aware datetime handling with `app/utils/timezone.py`
- Lazy evaluation for logging strings for performance

## Style Guidelines
- Use double quotes for strings
- FastAPI HTTPException for API errors
- Type hints required for all functions
- Descriptive variable and function names
- PEP 8 formatting
- PRs: Start with one-line summary, use sections (Changes, Testing, Environment Variables, Notes)