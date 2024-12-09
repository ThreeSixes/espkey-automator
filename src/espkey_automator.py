#!/usr/bin/env python3

import argparse
import json
from pprint import pprint
import os
import re

from lib import Configurator
from lib import ESPKey
from lib import Recipe


# If we're being called as a script.
if __name__ == "__main__":

    def process_args(args):
        """Process incoming argparase arguments.

        Args:
            args (Argparse): Parsed argparse arguments.

        Raises:
            ValueError: Exactly one action should be specified.
            ValueError: Weigand send data is invalid.

        Returns:
            dict: A dictionary containing the necessary data to execute ther equest.
        """

        action_spec = None
        action_ct = 0
        actions = ["delete_log", "get_config", "get_diagnostics", "get_log", "recipe",
                   "restart", "send_weigand"]
        args_unwrapped = {}

        for arg in vars(args):
            args_unwrapped.update({arg: getattr(args, arg)})

        for action in actions:
            if args_unwrapped[action]:
                action_spec = action
                action_ct += 1
        
        if action_ct != 1:
            action_args = []
            error_str = "You must specify exactly one action: "

            for action in actions:
                action = action.replace("_", "-")
                action_args.append(f"--{action}")
            
            error_str += ", ".join(action_args)

            raise ValueError(error_str)


        # This action rules them all.
        if args.recipe:
            return ("recipe", args.recipe)

        # Throw a ValueError if the weigand data isn't formatted correctly.
        if args.send_weigand:
            if not re.match(r"([0-9a-fA-F]+):([0-9]+)", args.send_weigand):
                raise ValueError("--send-weigand value is not properly formatted.")
        
        return action_spec


    # Get the argument parser going.
    parser = argparse.ArgumentParser(
            prog='espkey_automator',
            description='Execute actions against ESPKey devices.')

    parser.add_argument("--config", type=str, default="config.json",
                        help="Specify configuration file.")
    parser.add_argument("--delete-log", action="store_true", help="Delete the log on the device. " \
                        "Maybe used in combination with --with-post.")
    parser.add_argument("--with-post", action="store_true",  help="Use with --delete-log " \
                        "to trigger log deletion using a POST. Used with some versions of " \
                        "the ESPKey firmware that don't have a /delete endpoint.")
    parser.add_argument("--get-config", action="store_true", help="Get the ESPKey's config.")
    parser.add_argument("--get-diagnostics", action="store_true", help="Get diagnostic data from "\
                        "the ESPKey.")
    parser.add_argument("--get-log", action="store_true", help="Get logs from the ESPKey.")
    parser.add_argument("--get-log-file", type=str, default=None, help="Get logs an ESPKey test " \
                        "file. Human-redable timestamps can't be derived from a text file.")
    parser.add_argument("--get-version", action="store_true", help="Get ESPKey version data.")
    parser.add_argument("--recipe", type=str, default=None, help="Execute the specified recipe. " \
                        "This option is standalone. All configuration is derived from " \
                        "the recipe file.")
    parser.add_argument("--restart", action="store_true", help="Restart the ESPKey.")
    parser.add_argument("--send-weigand", type=str, help="Send weigand data with length in " \
                        "format 0aabbcc:26 where there is a hex string and bit length to send.")

    args = parser.parse_args()

    try:
        action = process_args(args)

    except ValueError as e:
        print(f"{e}\n")
        parser.print_help()

    # Recipes are a special case.
    if action == "recipe":
            rcp = Recipe(args.recipe)
            rcp.run()

    # Perform single action.
    else:
        # Configuration
        env_var_prefix = "EKA"
        config_file_override = os.getenv(f"{env_var_prefix}_CONFIG_FILE", args.config)
        configurator = Configurator(env_var_prefix=env_var_prefix, config_file=config_file_override)
        config = configurator.configuration

        ek = ESPKey(config)

        # Single action if/else stack.
        if action == "delete_log":
            if args.with_post:
                print(json.dumps(ek.delete_log(post_method=True)))
            else:
                print(json.dumps(ek.delete_log()))

        elif action == "get_config":
            print(json.dumps(ek.get_config()))

        elif action == "get_diagnostics":
            print(json.dumps(ek.get_diagnostics()))

        elif action == "get_log":
            print(json.dumps(ek.get_log()))

        elif action == "get_log_file":
            print(json.dumps(ek.get_log(file_name=args.get_log_file)))

        elif action == "get_version":
            print(json.dumps(ek.get_version()))

        elif action == "restart":
            print(json.dumps(ek.restart()))

        elif action == "send_weigand":
            weigand_parts = args.send_weigand.split(":")
            weigand_parts[1] = int(weigand_parts[1])
            print(json.dumps(ek.send_weigand(weigand_parts[0], weigand_parts[1])))

        else:
            print("Invalid action. Please specify an action.\n")
            parser.print_help()
        