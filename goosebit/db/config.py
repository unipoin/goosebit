from goosebit.settings import config
import logging
import re
import ssl
import sys

TORTOISE_CONF = {
    "connections": {"default": config.db_uri},
    "apps": {
        "models": {
            "models": ["goosebit.db.models", "aerich.models"],
        },
    },
}

if config.db_ssl_crt != "":
    try:
        creds = re.search("^postgres://(?P<user>[^:]+):(?P<password>[^@]+)@(?P<host>[^:]+):(?P<port>[^/]+)/(?P<database>[^?]+)(\\?(?P<parameters>.+))?$", config.db_uri).groupdict()
    except:
        logging.error(f"db_ssl_cert is defined! Then db_uri must to have the following style: postgres://<user>:<password>@<host>:<port>/<database>?sslmode=<sslmode>, please check you db_uri!")
        sys.exit()

    params = None

    if "parameters" in creds and creds["parameters"]:
        params = {x.split("=")[0]: x.split("=")[1] for x in creds["parameters"].split("&")}

    creds.pop("parameters")

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.load_verify_locations(config.db_ssl_crt)
    ssl_ctx.verify_mode = ssl.CERT_REQUIRED  # sets also check_hostname to True

    if params and params["sslmode"]:
        if params["sslmode"] == "none":
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
        elif params["sslmode"] == "optional":
            ssl_ctx.verify_mode = ssl.CERT_OPTIONAL
        elif params["sslmode"] == "require":
            ssl_ctx.verify_mode = ssl.CERT_REQUIRED

    creds["ssl"] = ssl_ctx

    TORTOISE_CONF['connections']['default'] = {
        "engine": "tortoise.backends.asyncpg",
        "credentials": creds
    }
    TORTOISE_CONF['apps']['models']['default_connection'] = "default"
