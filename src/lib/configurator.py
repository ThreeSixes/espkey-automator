import json
import os


class Configurator:
    def __init__(self, config_file=None, env_var_prefix=None, args={}):
        """Configurator

        Args:
            config_file (str, optional): Name of a JSON-formatted config file to use. Defaults to None.
            env_var_prefix (str, optional): Environment variable prefix prepended to env vars. Defaults to None.
            args (dict, optional): Initial configuration options. Defaults to {}.
        """

        # Configuration keys required.
        self.__required_items_per_ek = [
            "base_url",
            "web_user",
            "web_pass",
        ]

        # Built-in defaults.
        self.__config = {
        }

        # Type conversions for configuration values.
        self.__config_type_conversions = {
        }

        # Pass through our config file.
        self.__config_file = config_file

        # Environment variable prefix.
        self.__env_var_prefix = env_var_prefix

        # Configure!
        self.__configure(args)


    def __configure(self, args):
        """Create a configuration from a variety of sources. Each source is overriden by the next.
        1) Defaults specified in the constructor
        2) JSON configuration file if specified
        3) Environment variables
        4) Arguments sent in

        Args:
            args (dict): Initially-specified arguments.

        Raises:
            KeyError: Indicates a missing mandatory config option.
        """

        # Die on an error
        die = False

        # Load configuration from files.
        if self.__config_file is not None:
            self.__configure_from_file()

        # Configure from environment variables.
        self.__configure_from_env()

        # Add any incoming arguments.
        self.__config.update(args)

        # Validate that we have all our configuration.
        for target in self.__config:
            for item in self.__required_items_per_ek:
                if item not in self.__config[target]:
                    print(f"Error: Required configuration item missing: {target}.{item}")
                    die = True

        # Type conversions
        for item in self.__config:
            if item in self.__config_type_conversions:
                try:
                    self.__config[item] = self.__config_type_conversions[item](self.__config[item])

                except ValueError:
                    arg_type = self.__config_type_conversions[item].__name__
                    print(f"Error: '{item}' must be of type '{arg_type}'.")
                    die = True

        if die:
            print("Error: Invalid configuaration. Exiting.")
            exit(1)


    def __configure_from_env(self):
        """Load configuration from environment variables.
        """
        env_vars = os.environ

        # Search for any of our items in environment variables.
        for item in self.__required_items_per_ek:
            if self.__env_var_prefix:
                item_upper = f"{self.__env_var_prefix}_{item.upper()}"
            else:
                item_upper = item.upper()

            # If we have a match use it.
            if item_upper in env_vars:
                self.__config.update({item: env_vars[item_upper]})


    def __configure_from_file(self):
        """Load configuration from a JSON file.
        """
        if self.__config_file is not None:
            with open(self.__config_file, "r") as f:
                contents = f.read()
                self.__config.update(json.loads(contents))


    @property
    def configuration(self):
        """A dictionary containing the configuration.
        """

        return self.__config
