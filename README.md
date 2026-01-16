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

### API

TODO

### Database

TODO

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
