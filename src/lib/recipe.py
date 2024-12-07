import datetime
import json
from pprint import pprint

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

        self.__log_file = self.__recipe['config']['log_file']

        # ESPKey objects by name.
        self.__espkeys = {}
        self.__hydrate_espkeys()

        self.__operations = {
            "delete_log",
            "get_config",
            "get_diagnostics",
            "get_log",
            "get_version",
            "restart",
            "send_weigand"
        }


    @staticmethod
    def __validate_config(config):
        errors = []
        valid = True

        if len(config) == 0:
            valid = False
            errors.append("*: The config key can't be empty.")
 
        else:
            if "log_file" not in config:
                valid = False
                errors.append("log_file: A log_file must be specified.")

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


    @staticmethod
    def __validate_tasks(config):
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
        required_top_level_keys = ["config", "espkeys", "tasks"]

        top_level_key_validators = {
            "config": self.__validate_config,
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
        for task in self.__recipe['tasks']:
            this_task = self.__recipe['tasks'][task]
            target_name = this_task['target']
            target = self.__espkeys[target_name]

            # Loop through actions.
            for action in this_task['actions']:
                if action['operation'] == "get_log":
                    now = datetime.datetime.utcnow()
                    pretty_json = True

                    log_data = {
                        "entries": target.get_log(),
                        "metadata": {
                            "espkey": target_name,
                            "retrived": now.isoformat()
                        }
                    }

                    if action['file_action'] == "store_with_date":
                        json_dumps_kwargs = {}

                        file_name = f"{now.strftime("%Y%m%d-%H%M%S%f")}_{target_name}_log.json"

                        if 'pretty_json' in action:
                            pretty_json=bool(action['pretty_json'])
                        
                        if pretty_json:
                            json_dumps_kwargs = {
                                "indent": 4
                            }                        

                        with open(file_name, "w") as f:
                            json_str = json.dumps(log_data, **json_dumps_kwargs)
                            f.write(json_str)
                        
                        print(f"Wrote log: {file_name}")