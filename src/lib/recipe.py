import datetime
import json
from pprint import pprint
import re
import time

from .espkey import ESPKey


class InvlalidRecipe(ValueError):
    pass

class Recipe:
    def __init__(self, recipe_file):
        """Automator recipe

        Args:
            recipe_file (str): File to load recpie from.
        """

        self.__file_name = recipe_file

        # Load configuration from file.
        self.__recipe = self.__load_json(recipe_file) 

        # Run recipe validator.
        self.__validate_recipe()

        # ESPKey objects by name.
        self.__espkeys = {}
        self.__hydrate_espkeys()


    def __validate_send_weigand(self, config):
        """Validate specified weigand data.

        Args:
            config (dict): send_weigand object.

        Returns:
            tuple(bool, list): Flag indicating valid data is valid and a list of errors.
        """

        errors = []
        valid = True

        if len(config) == 0:
           valid = False
           errors.append("*: The send_weigand key can't be empty.")

        else:
            if "data" not in config:
                valid = False
                errors.append("data: A data string must be specified.")

            else:
                if not re.match(r"^([0-9a-fA-f]+)\:([0-9]+)$", config['data']):
                    valid = False
                    errors.append("data: Invalid data format. It should ben in the format " \
                        "00aabbcc:26  where 00aabbcc is the hex representation of the weigand " \
                        "data and 26 is the length to transmit in bits.")
            
        return (valid, errors)


    @staticmethod
    def __validate_espkeys(config):
        """ Validate espkey specifiers.

        Args:
            config (dict): ESPKeys configuration section.

        Returns:
            tuple: Tuple with a validity flag [0] and a list of errors [1].
        """

        errors = []
        valid = True

        if len(config) == 0:
            valid = False
            errors.append("*: One or more ESPKeys must be specified with a "\
                "base_url\" and optional \"web_user\" and \"web_password\".")
 
        else:
            for espkey in config:
                if "base_url" not in config[espkey]:
                    valid = False
                    errors.append(f"{espkey}: A base_url must be specified with " \
                        "an optional \"web_user\" and \"web_password\".")

        return (valid, errors)


    def __validate_tasks(self, config):
        """Validate tasks in a given config segment.

        Args:
            config (dict): Tasks configuratoin segment.

        Returns:
            tuple(bool, list): Tuple containing a boolean value flagging the validity of the
                               config and a list of errors.
        """

        errors = []
        valid = True

        if len(config) == 0:
            valid = False
            errors.append("* The tasks key can't be empty.")
        
        for task in config:
            has_actions = True
            this_task = config[task]

            if "actions" not in this_task:
                valid = False
                errors.append(f"{task}: Must contain an \"actions[]\".") 
                has_actions = False

            if has_actions:
                action_ct = 0

                for action in this_task['actions']:
                    if "operation" not in action:
                        valid = False
                        errors.append(f"{task}.actions.{action_ct}: Must contain an \"operation\".") 

                    else:
                        if action["operation"] == "send_weigand":
                            send_weigand_validator = self.__validate_send_weigand(action)

                            if send_weigand_validator[0] is False:
                                valid = False
                                for error in send_weigand_validator[1]:
                                    errors.append(f"{task}.actions.{action_ct}: {error}") 

                        elif action["operation"] == "delay":
                            if 'sec' in action:
                                if (action['sec']):
                                    if not (isinstance(action['sec'], int) or
                                            isinstance(action['sec'], float)):
                                        valid = False
                                        errors.append(f"{task}.actions.{action_ct}: " \
                                            "'sec' must be an int or float. ")
                            else:
                                valid = False
                                errors.append(f"{task}.actions.{action_ct}: " \
                                    "'sec' is required.") 

                    action_ct += 1

        return (valid, errors)


    def __validate_recipe(self):
        """Validate the specified recpie

        Args:
            recipe_dict (dict): Recipe dictionary.

        Raises:
            InvlalidRecipe: The recipe isn't valid.

        Returns:
            bool: True for a valid recipe.
        """

        # Store information about config validity.
        valid = True
        description_text = ""
        error_descriptors = []

        # Top level config keys
        required_top_level_keys = ["espkeys", "tasks"]

        top_level_key_validators = {
            "espkeys": self.__validate_espkeys,
            "tasks": self.__validate_tasks
        }

        # Validate options
        for top_level_key in required_top_level_keys:
            if top_level_key not in self.__recipe:
                valid = False
                error_descriptors.append(f"Missing top level key: \"{top_level_key}\".")

            else:
                # Validate top-level key contents
                results = top_level_key_validators[top_level_key](self.__recipe[top_level_key])
                
                if results[0] is False:
                    valid = False
                    error_descriptors.append(f" - {top_level_key}.{results[1]}")

        # If the configuration was invalidated at any point...
        if valid is False:
            description_text = f"Recipe \"{self.__file_name}\" contains the following errors:\n"

            for error in error_descriptors:
                description_text += f" = {error}\n"

            raise InvlalidRecipe(description_text)

        return valid


    def __hydrate_espkeys(self):
        """Create the necessary ESPKey objects to execute the recipe.
        """

        for espkey in self.__recipe['espkeys']:
            this_ek_config = self.__recipe['espkeys'][espkey]
            ek_config = {"base_url": this_ek_config['base_url']}

            # If we have creds use them.
            if 'web_user' in this_ek_config and \
                'web_pass' in this_ek_config:

                ek_config.update({
                    'web_user': this_ek_config['web_user'],
                    'web_pass': this_ek_config['web_pass']
                })

            self.__espkeys.update({espkey: ESPKey(ek_config)})


    def __load_json(self, file_name):
        """Load JSON data from a file specified by file_name.

        Args:
            file_name (str): Recipe file to load.

        Returns:
            dict: Loaded configuration.
        """

        recipe = {}

        with open(file_name, "r") as f:
            recipe = json.loads(f.read())

        return recipe


    def run(self):
        """Execute the recipe.
        """

        for task in self.__recipe['tasks']:
            run_start = datetime.datetime.utcnow()
            this_task = self.__recipe['tasks'][task]
            target_name = this_task['target']
            target = self.__espkeys[target_name]

            file_name = f"{run_start.strftime("%Y%m%d-%H%M%S")}_{target_name}_{task}.json"

            log_data = {
                "actions": [],
                "metadata": {
                    "espkey": target_name,
                    "run_start": run_start.isoformat()
                }
            }

            # Loop through actions.
            for action in this_task['actions']:
                pretty_json = True
                now = datetime.datetime.utcnow()
                json_dumps_kwargs = {}

                action_data = {
                    "action": action['operation'],
                    "run": now.isoformat()
                }

                # Get log data
                if action['operation'] == "get_log":
                    action_data.update({
                        "result": target.get_log()
                    })

                # Delete logs
                elif action['operation'] == "delete_log":
                    with_post = False

                    if 'with_post' in action:
                        with_post = bool(action['with_post'])
                    
                    kwargs_delete = {"post_method": with_post}

                    action_data.update({
                        "result": target.delete_log(**kwargs_delete)
                    })

                # Get diagnostics
                elif action['operation'] == "get_diagnostics":
                    action_data.update({
                        "result": target.get_diagnostics()
                    })

                # Get config
                elif action['operation'] == "get_config":
                    action_data.update({
                        "result": target.get_config()
                    })

                # Get config
                elif action['operation'] == "get_config":
                    action_data.update({
                        "result": target.get_config()
                    })

                # Get version
                elif action['operation'] == "get_version":
                    action_data.update({
                        "result": target.get_version()
                    })

                # Restart
                elif action['operation'] == "restart":
                    action_data.update({
                        "result": target.restart()
                    })

                # Send weigand
                elif action['operation'] == "send_weigand":
                    weigand_parts = action['data'].split(":")
                    weigand_parts[1] = int(weigand_parts[1])

                    action_data.update({
                        "result": target.send_weigand(weigand_parts[0], weigand_parts[1])
                    })

                # Delay
                elif action['operation'] == "delay":
                    time.sleep(action['sec'])
                    action_data.update({"delay": action['sec']})


                log_data['actions'].append(action_data.copy())


            # Write log data and inform user.
            if 'pretty_json' in this_task:
                pretty_json=bool(this_task['pretty_json'])
            
            if pretty_json:
                json_dumps_kwargs.update({
                    "indent": 4
                })

            with open(file_name, "w") as f:
                json_str = json.dumps(log_data, **json_dumps_kwargs)
                f.write(json_str)
            
            print(f"Wrote log: {file_name}")