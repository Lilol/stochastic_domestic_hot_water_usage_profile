from os import makedirs
from os.path import join

from optimization_configuration.network.definitions import Network
from utility.utility import suffix_or_empty


class NetworkConfigFileNames:
    """Manages file names for network configurations."""
    def __init__(self, output_directory):
        """Initializes the NetworkConfigFileNames with an output directory."""
        self.__output_directory = output_directory
        makedirs(output_directory, exist_ok=True)

    def __dir(self, network):
        """Returns the directory for a given network."""
        return join(self.__output_directory, f"{network.value}")

    def consumption_profile_filename(self, **kwargs):
        """Returns the file name for the consumption profile."""
        return self.profile_filename("profiles.csv", **kwargs)

    def generic_network_filename(self, base_filename, ext="yaml", **kwargs):
        """Returns a generic network file name."""
        if ext != "" and '.' in base_filename:
            base_filename = base_filename.split('.')[0]
        base_filename = f"{base_filename}.{ext}"
        dir = self.assemble_output_directory(**kwargs)
        makedirs(dir, exist_ok=True)
        return join(dir, base_filename)

    def profile_filename(self, base_filename, **kwargs):
        """Returns the file name for a profile."""
        return self.generic_network_filename(base_filename, ext="csv", **kwargs)

    def assemble_output_directory(self, **kwargs):
        """Assembles the output directory path."""
        dir = self.__dir(kwargs.pop("network", Network.INVALID))
        dir_part = "".join(suffix_or_empty(val, sep='' if i == 0 else '_') for i, (_, val) in
                           enumerate(kwargs.items()))
        return join(dir, dir_part)
