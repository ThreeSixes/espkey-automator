import json

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
                if "base_url" not in espkey:
                    valid = False
                    errors.append(f"{espkey}: A base_url must be specified with " \
                        "an optional \"web_user\" and \"web_password\".")

        return (valid, errors)


    @staticmethod
    def __validate_tasks(config):
        errors = []
        valid = False

        if len(config) == 0:
            valid = False
            errors.append("* The tasks key can't be empty.")
        
        for task in config:
            if "operation" not in task:
               errors.append(f"{task}: Must contain an \"operation\".") 

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
        for espkey in self.__recipe['espkeys']:
            this_ek_config = self.__recipe['espkeys'][espkey]
            ek_kwargs = {"base_url": this_ek_config['base_url']}

            if 'web_user' in this_ek_config and \
                'web_pass' in this_ek_config:

                ek_kwargs.update({})



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
        pass