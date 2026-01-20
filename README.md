# Smartlock-Authentication-Authorization

Core Auth and aut for the Smartlock project

## Deployment

### Keycloak

#### Starting the service

Move to the docker/keycloak folder and run:

```bash
cp .env.example .env
```

Update the `.env` file and care to change these in particular:

- `POSTGRES_PASSWORD`: Set a strong password for the Keycloak database user (max 32 characters).
- `KC_BOOTSTRAP_ADMIN_PASSWORD`: Set a strong password for the Keycloak temporary admin user.

Then, run the following command to start Keycloak:

```bash
docker-compose up -d
```

Access the Keycloak domain: `https://auth.devinci-fablab.fr`.

#### Configuration

Login with the temporary admin user created during deployment.

Create a new admin user for regular use and delete the temporary one.

TODO: Add email configuration

TODO: set password, totp and session policies for security

TODO: Check user config (roles, groups, etc.) which groups to create (president, secretaire, tresorier, codir, coges, responsables, pole, membre, etc.)

TODO: Create first client for SmartLock

### API & Database

#### Starting the service

Move to the docker/database folder and run:

```bash
cp .env.example .env
```

Update the `.env` file and care to change these in particular:

- `POSTGRES_PASSWORD`: Set a strong password for the PostgreSQL database user.

Then, run the following command to start the API and database services:

```bash
docker-compose up -d
```

The API will be accessible at `http://localhost:8000` (or your configured host).

#### Configuration

Once the services are running:

1. Apply existing migrations (Standard setup): This creates the tables based on the migration files already in the code.

```bash
docker compose exec api_app uv run alembic upgrade head
```

2. If not :

```bash
docker compose exec api_app uv run alembic revision --autogenerate -m "initial migration"
docker compose exec api_app uv run alembic upgrade head
```

. View the migration history:

```bash
docker compose exec api_app uv run alembic history
```

3. Verify the API is running by accessing the docs endpoint:

```
http://localhost:8000/docs
```

4. Ensure the database connection is healthy and tables are created.

TODO: Set up database backup strategy

TODO: Configure API environment variables (JWT secrets, authentication settings, etc.)

TODO: Add API rate limiting and throttling

TODO: Set up logging and monitoring for database and API

TODO: Create seed data or initial fixtures for testing

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
