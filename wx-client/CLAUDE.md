# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Information
- WeChat Mini Program for glucose tracking and meal management
- Part of the Gluco monorepo project, works with FastAPI backend (`../backend`)
- Uses JavaScript (no TypeScript) with WeChat Mini Program framework

## Development Commands
**Note:** Development occurs within the `wx-client/` directory of the monorepo.

- No explicit build/lint/test commands defined in package.json
- Development typically occurs in WeChat Developer Tools

## Code Style Guidelines
- **Naming**: camelCase for variables/functions, kebab-case for files/directories
- **Imports**: Use CommonJS require() statements
- **Functions**: Prefer regular function declarations over arrow functions
- **Error Handling**: Use .then/.catch chains and catch() blocks with appropriate UI feedback
- **Async**: Use Promise chains with .then/.catch for async operations
- **Comments**: JSDoc-style for functions, inline comments for complex logic
- **Architecture**: Modular with clear separation between UI, business logic, and API

## WeChat Mini Program Guidelines
- Stick to chaining style when handling async processes
- Use /weixin/auth route for authentication
- Follow standard Page() and Component() structure
- Use WXML binding syntax with {{ variable }} for data binding

## Backend Integration
- Backend service located at `../backend/`
- API endpoints defined in `utils/api.js` map to `../backend/app/routers/`
- Authentication flow integrates with `../backend/app/routers/weixin_auth.py`
- Image processing handled by `../backend/app/routers/jobs.py`

## Documentation
- API specifications in reference/openapi.json
- WeChat Mini Program documentation in docs/ directory