#!/usr/bin/env python3

import argparse
import os
from pprint import pprint
import time

from lib import Configurator
from lib import ESPKey


# Configuration
env_var_prefix = "EKA"
config_file_override = os.getenv(f"{env_var_prefix}_CONFIG_FILE", "./config.json")
configurator = Configurator(env_var_prefix=env_var_prefix, config_file=config_file_override)
config = configurator.configuration

# Create ESPKey
ek = ESPKey(config)

#pprint(ek.get_version())
#pprint(ek.get_config())
#pprint(ek.get_log())
#pprint(ek.get_log(file_name="test.txt"))
#pprint(ek.delete_log(post_method=True))
#pprint(ek.send_weigand("09adc39", 26))
pprint(ek.get_log())
#pprint(ek.get_diagnostics())

#if __name__ == "__main__":
#    parser = argparse.ArgumentParser(
#            prog='espkey_automator',
#            description='Execute actions against ESPKey devices.')

