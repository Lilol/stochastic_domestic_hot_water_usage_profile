from configparser import RawConfigParser, ExtendedInterpolation
from os import getcwd
from os.path import join
from sys import argv


class ConfigurationManager:
    """Manages the application's configuration settings."""
    def __init__(self, config_filename=join(getcwd(), "config", "config.ini")):
        """Initializes the ConfigurationManager."""
        self.__config = RawConfigParser(allow_no_value=True, interpolation=ExtendedInterpolation())
        self.__config.read_file(open(config_filename))
        self._registered_entries = {}

    def getarray(self, section, key, dtype=str, fallback=None):
        """Gets a configuration value as an array."""
        val = self._get(section, key, fallback=fallback)
        try:
            return [dtype(v) for v in val]
        except TypeError:
            return [dtype(val), ]

    def get(self, section, key, fallback=None):
        """Gets a configuration value."""
        if section not in self._registered_entries or key not in self._registered_entries[section]:
            return self._get(section, key, fallback)
        return self._registered_entries[section][key]()

    def _get(self, section, key, fallback=None):
        """A private method to get a configuration value."""
        try:
            value = self.__config.get(section, key, fallback=fallback)
        except Exception as e:
            raise KeyError(f"Section '{section}', key '{key}' problem in configuration: '{e}'")
        if value is None:
            raise KeyError(f"Section '{section}', key '{key}' not found in configuration")

        if "," not in value:
            return value

        return list(filter(len, value.strip('][').split(',')))

    def set(self, section, key, value):
        """Sets a configuration value."""
        self.__config.set(section, key, value)

    def setboolean(self, section, key, value):
        """Sets a boolean configuration value."""
        boolean_str = 'True' if value else 'False'
        self.__config.set(section, key, boolean_str)

    def getboolean(self, section, key, fallback=None):
        """Gets a boolean configuration value."""
        return self.__config.getboolean(section, key, fallback=fallback)

    def getint(self, section, key, fallback=None):
        """Gets an integer configuration value."""
        return self.__config.getint(section, key, fallback=fallback)

    def getfloat(self, section, key, fallback=None):
        """Gets a float configuration value."""
        return self.__config.getfloat(section, key, fallback=fallback)

    def has_option(self, section, option):
        """Checks if a configuration option exists."""
        return self.__config.has_option(section, option)


# init_config
config_file = argv[2] if len(argv) >= 3 else join(getcwd(), 'config', 'config.ini')
config = ConfigurationManager(config_filename=config_file)
