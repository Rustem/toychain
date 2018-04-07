import os
import json
from ccoin.dict_tools import LazyDict, merge_deep

AppConfig = LazyDict({
    "base_path": os.path.expanduser("~/.ccoin"),
    "account_address": "",
    "storage_path": os.path.join("{base_path}", "{account_address}"),
    "key_dir": os.path.join("{storage_path}", ".keys"),
    "chain_db": "blockchain",
    "state_db": "worldstate",
    "discovery_service": {
        "host": "192.168.0.1",
        "port": 8000,
        "proto": "http"
    },
    "pj": os.path.join
})


def configure(app_config=None):
    """
    Configures app
    :param app_config: app configuration object
    :type app_config: dict
    """
    if app_config is None:
        return
    global AppConfig
    if 'app' in app_config:
        AppConfig = merge_deep(app_config.pop('app'), AppConfig)
    if 'client' in app_config:
        AppConfig = merge_deep(app_config.pop('client'), AppConfig)
    AppConfig = merge_deep(app_config, AppConfig)

def configure_from_file(config_path):
    """
    :param config_path:
    :return:
    :raises: FileNotFoundError
    """
    with open(config_path, "r") as fh:
        app_config = json.load(fh)
        configure(app_config=app_config)