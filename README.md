<img src="https://github.com/user-attachments/assets/316f1b09-9a2d-4b8a-98bc-aca9c4fb0d78" style="width: 30em;"><br>
ytpmvsd is a website for catalouging YTPMV Samples, with accompanying tools/features to integrate it further into existing workflows.

---

## Setup

Start by copying `.example.env` to `.env` and setting the following:

- `DATABASE_URL`: URL for your PostgresSQL database. Yes, it has to be PostgresSQL, nothing else supports the ARRAY data type.
- `FLASK_SECRET_KEY`: You can set this to anything. For deployment, you'll obviously want to set it to something sufficiently random, for security purposes
- `SAMPLES_PER_PAGE`: The amount of samples shown per page on `/samples/`. This is set to 24 by default.
- `VERSION`: The version of the site. This is used for grabbing the latest changelog.

Development of this is done in a venv. The venv must be Python 3.12 and must be called either `ytpmvsd_env` or `.venv` as these are what the .gitignore is set to ignore.

`virtualenv --python=python3.12 ytpmvsd_env`

After setting that up and activating the environment, run `pip install -r requirements.txt`.

> **NOTE**: If you are on a distro where development headers are in a separate package (Ubuntu, Fedora, etc.) you will have to download the development package for Python 3.12 in order to compile psycopg2

After all that, do `flask run`.
