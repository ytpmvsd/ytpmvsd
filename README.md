<img src="https://github.com/user-attachments/assets/316f1b09-9a2d-4b8a-98bc-aca9c4fb0d78" style="width: 30em;"><br>
ytpmvsd is a website for catalouging YTPMV Samples, with accompanying tools/features to integrate it further into existing workflows.

---

## Setup

Start by copying `config.example.toml` to `config.toml` and setting the following values:

- `database_url`: URL for your PostgresSQL database. Currently, nothing else is supported
- `flask_secret_key`: The key that Flask uses for cryptography. You can set this to anything. For deployment, you'll obviously want to set it to something sufficiently random, for security purposes

There are other values you can set, but they're all set by default in the example file and can be changed according as their comments describe.

Development of this is done in a venv. The venv must be Python 3.12 and must be called either `ytpmvsd_env` or `.venv` as these are what the .gitignore is set to ignore.

`virtualenv --python=python3.12 ytpmvsd_env`

After setting that up and activating the environment, run `pip install -r requirements.txt`.

> **NOTE**: If you are on a distro where development headers are in a separate package (Ubuntu, Fedora, etc.) you will have to download the development package for Python 3.12 in order to compile psycopg2

After all that, do `flask run`.

## Translations

### Extracting strings
To extract all translatable strings and update the template:
`pybabel extract -F babel.cfg -o messages.pot .`

### Initializing a new language
To add a new language (e.g., Japanese):
`pybabel init -i messages.pot -d translations -l ja`

### Updating translations
After adding new strings to the code or templates, update the catalogs:
`pybabel update -i messages.pot -d translations`

### Compiling translations
To compile the translations for use:
`pybabel compile -d translations`
