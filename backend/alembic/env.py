from logging.config import fileConfig
import os
from typing import Any
from sqlalchemy import engine_from_config, pool
from alembic import context


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config: Any = context.config  # type: ignore

# Update the default URL to MySQL
config.set_section_option(config.config_ini_section, "sqlalchemy.url", os.getenv("DATABASE_URL", "mysql+pymysql://root@localhost:3306/gluco"))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models here for Alembic to detect
from app.database.database import Base

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(  # type: ignore
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
    )

    with context.begin_transaction():  # type: ignore
        context.run_migrations()  # type: ignore

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(  # type: ignore
            connection=connection, 
            target_metadata=target_metadata,
        )

        with context.begin_transaction():  # type: ignore
            context.run_migrations()  # type: ignore

if context.is_offline_mode():  # type: ignore
    run_migrations_offline()
else:
    run_migrations_online()
