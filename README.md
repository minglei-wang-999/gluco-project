# Gluco Backend

A FastAPI-based backend service for analyzing food images and providing nutritional insights with a focus on glycemic impact.

## Features

• Image Analysis - Process food images to identify ingredients and their nutritional content
• Glycemic Load Calculation - Calculate meal glycemic load and provide personalized recommendations
• User Management - Complete authentication system with email verification
• WeChat Integration - Support for WeChat Mini Program authentication and cloud storage
• Nutrition History - Track and analyze users' meal history and nutritional patterns

## Tech Stack

• Python 3.11+
• FastAPI - Modern web framework for building APIs
• SQLAlchemy - SQL toolkit and ORM
• Alembic - Database migration tool
• Poetry - Dependency management
• pytest - Testing framework
• MySQL - Database
• GitHub Actions - CI/CD pipeline

## Prerequisites

• Python 3.11 or higher
• Poetry for dependency management
• MySQL database
• WeChat Mini Program developer account (for WeChat integration)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/gluco-backend.git
cd gluco-backend
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Set up environment variables:
```bash
cp .env.example .env
```

Edit `.env` file with your configuration:
```
DATABASE_URL=mysql+pymysql://user:password@localhost/dbname
SECRET_KEY=your-secret-key
WEIXIN_APPID=your-wechat-appid
WEIXIN_SECRET=your-wechat-secret
WEIXIN_ENV_ID=your-wechat-cloud-env
OPENAI_API_KEY=your-openai-api-key
```

4. Run database migrations:
```bash
poetry run alembic upgrade head
```

## Development

1. Start the development server:
```bash
poetry run uvicorn app.main:app --reload
```

2. Run tests:
```bash
poetry run pytest
```

3. Generate test coverage report:
```bash
poetry run pytest --cov=app tests/
```

## CI/CD Pipeline

#### Test
GitHub Actions for continuous integration:

• Linting - Checks code quality
• Testing - Runs the test suite against a MySQL test database
• Database migrations - Automatically applies migrations before running tests

#### Deployment
The deployment is done by Weixin Cloud streamline which will monitor any commit to `main` branch regardless of the Github Actions.

It will look for the Dockerfile and build the image and start the container in sequence. 

The database migration is done in the Dockerfile before uvicorn is started.

#### Display current migration head
```bash
export DATABASE_URL=mysql+pymysql://[user]:[password]@[database_url]/gluco
poetry run alembic current
```

## API Documentation

Once the server is running, access the API documentation at:
• Swagger UI: http://localhost:8000/docs
• ReDoc: http://localhost:8000/redoc

## Main Endpoints

• POST /process-image - Analyze food image and get nutritional insights
• POST /users/register - Register new user
• POST /users/login - User authentication
• GET /nutrition/history - Get user's meal history
• GET /meals/metrics - Get user's nutritional metrics

## Docker Deployment

1. Build the Docker image:
```bash
docker build -t gluco-backend .
```

2. Run the container:
```bash
docker run -p 8000:8000 -d gluco-backend
```

## Testing

The project uses pytest for testing. Run the test suite:

```bash
poetry run pytest
```

For test coverage report:
```bash
poetry run pytest --cov=app tests/
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Write tests for new features
4. Ensure all tests pass
5. Submit a pull request with a detailed description following the PR template

## Pull Request Guidelines

When submitting a PR, please include:
• A one-line summary of changes
• Detailed description of changes made
• Testing procedures followed
• Any required environment variables
• Additional notes or considerations

## License

[Your License] 