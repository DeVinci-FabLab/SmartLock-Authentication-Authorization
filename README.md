# Smartlock-Authentication-Authorization

Core Auth and aut for the Smartlock project

## Deployment

### Keycloak

#### Starting the service

Create the volumes workspace:

```bash
mkdir -p /home/debian/docker/volumes/keycloak/conf
mkdir -p /home/debian/docker/volumes/keycloak/postgres_data
```

Get the Keycloak compose.yml and .env.example files:

```bash
mkdir -p /home/debian/docker/utilities/keycloak
cd /home/debian/docker/utilities/keycloak
wget https://raw.githubusercontent.com/Devinci-Fablab/SmartLock-Authentication-Authorization/main/docker/keycloak/compose.yml
wget https://raw.githubusercontent.com/Devinci-Fablab/SmartLock-Authentication-Authorization/main/docker/keycloak/.env.example
```

Move to the `docker/keycloak` folder and run:

```bash
cp .env.example .env
```

Update the `.env` file and care to change these in particular:

- `POSTGRES_PASSWORD`: Set a strong password for the Keycloak database user (max 32 characters).
- `KC_BOOTSTRAP_ADMIN_PASSWORD`: Set a strong password for the Keycloak temporary admin user.

Using openssl to generate strong passwords:

```bashbash
openssl rand -base64 32
```

Finally, make the file more private:

```bash
sudo chmod 600 .env
```

Then, run the following command to start Keycloak:

```bash
docker-compose up -d
```

Be sure to have on OVH a redirection from `auth.devinci-fablab.fr` to `193.70.33.226` so Traefik can route the traffic to the Keycloak container.

Access the Keycloak domain: `https://auth.devinci-fablab.fr`.

#### Configuration

Login with the temporary admin user created during deployment `KC_BOOTSTRAP_ADMIN_USERNAME` and `KC_BOOTSTRAP_ADMIN_PASSWORD`.

Create a new admin user for regular use and delete the temporary one for security: Go to "Users" > "Add user", fill in the details, and then set a password for this user and give him all admin permissions. Sign out, sign in as the new admin user. Finally, delete the temporary admin user and set up 2FA for the new admin user.

Go to Configure > Realm Settings > Login and set the following policies:

- User registration: OFF
- Forgot password: ON
- Remember Me: ON

- Verify email: ON

Then go to Email and set up the email configuration to enable email verification and password reset features.

Go to Localization and set the default locale to French (France) and enable internationalization support.

Go to Sessions and set:

- SSO Session Idle: 30 minutes
- SSO Session Max: 10 hours
- SSO Session Idle Remember Me: 1 day
- SSO Session Max Remember Me: 30 days

Go to user profile and add custom attribute:

- `card_id`: ...

Go to Configure > Authentication > Required actions and set:

- Configure OTP: ON and default ON
- Verify email: ON and default ON
- Update password: ON and default ON

TODO: Check user config (roles, groups, etc.) which groups to create (president, secretaire, tresorier, codir, coges, responsables, pole, membre, etc.)

TODO: Create first client for SmartLock

TODO: Create a Service Account for the API and generate credentials

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
