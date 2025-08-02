# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Gluco Project** - a monorepo combining a WeChat Mini Program frontend (`wx-client`) and a FastAPI backend (`backend`) for glucose tracking, nutritional analysis, and meal management.

### Architecture
- **Frontend**: WeChat Mini Program (JavaScript) for mobile glucose tracking
- **Backend**: FastAPI service with OpenAI Vision API integration for food image analysis
- **Database**: MySQL with comprehensive migration system
- **Authentication**: Dual system supporting both email users and WeChat OpenID users

## Repository Structure

```
gluco-project/
├── backend/           # FastAPI backend service
│   ├── app/          # Main application code
│   ├── alembic/      # Database migrations
│   ├── tests/        # Test suite
│   └── docs/         # Backend documentation
├── wx-client/        # WeChat Mini Program
│   ├── pages/        # WeChat pages
│   ├── components/   # Reusable components
│   ├── utils/        # Utility functions
│   └── docs/         # Frontend documentation
└── resources/        # Shared resources

```

## Development Commands

### Backend (FastAPI)
```bash
cd backend
poetry run uvicorn app.main:app --reload    # Development server
poetry run pytest                           # Run tests
poetry run alembic upgrade head            # Run migrations
```

### Frontend (WeChat Mini Program)  
- Development occurs in WeChat Developer Tools
- No explicit build commands - uses WeChat's built-in tooling

## Key Features
- **Food Image Analysis**: AI-powered nutritional analysis using OpenAI Vision API
- **Dual Authentication**: Email-based users and WeChat OpenID integration
- **Subscription System**: Payment processing with subscription management
- **Multi-platform Storage**: WeChat cloud storage integration
- **Comprehensive Testing**: Full test coverage with database isolation

## API Integration Overview

The wx-client communicates with the backend through well-defined REST endpoints:

### Core Endpoints Used by Frontend
- **Authentication**: `/weixin/auth/login`, `/weixin/auth/profile`
- **Subscriptions**: `/subscriptions/status`, `/subscriptions/payment`, `/subscriptions/update`
- **Meals**: `/meals`, `/meals/history`, `/meals/metrics`
- **Image Processing**: `/jobs/process-image`, `/jobs/process-image-async`, `/jobs/tasks/{id}`
- **Utilities**: `/health`, `/jobs/temp-url`, `/jobs/query-nutritions`

### Authentication
- **Frontend**: Uses WeChat OpenID via `wx-client/utils/api.js`
- **Backend**: JWT tokens with dual user system (WeChat + email users)
- **Documentation**: See `wx-client/docs/authentication.md` for detailed flow

### Request Architecture  
- **Development**: Standard HTTP requests via `wx.request`
- **Production**: WeChat Cloud Container via `wx.cloud.callContainer`
- **Documentation**: See `wx-client/docs/request_methods.md` for implementation details 