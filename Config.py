from Schema import SCHEMA

from tomllib import load
from cerberus import Validator

def LoadConf():
    v_ref = Validator(SCHEMA)

    with open("config.toml", 'rb') as file:
        config = load(file)

    if v_ref.validate(config):
        return config
    else:
        print(v_ref.errors)
        raise ValueError("Bad config")
