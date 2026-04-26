from Schema import SCHEMA

from tomllib import load
from cerberus import Validator

with open("config.toml", 'rb') as file:
    config = load(file)

v_ref = Validator(SCHEMA)
print(v_ref.validate(config))
print(v_ref.errors)
