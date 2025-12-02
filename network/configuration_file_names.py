from os import makedirs
from os.path import join

from optimization_configuration.network.definitions import Network
from utility.utility import suffix_or_empty


class NetworkConfigFileNames:
    def __init__(self, output_directory):
        self.__output_directory = output_directory
        makedirs(output_directory, exist_ok=True)

    def __dir(self, network):
        return join(self.__output_directory, f"{network.value}")

    def consumption_profile_filename(self, **kwargs):
        return self.profile_filename("profiles.csv", **kwargs)

    def generic_network_filename(self, base_filename, ext="yaml", **kwargs):
        if ext != "" and '.' in base_filename:
            base_filename = base_filename.split('.')[0]
        base_filename = f"{base_filename}.{ext}"
        dir = self.assemble_output_directory(**kwargs)
        makedirs(dir, exist_ok=True)
        return join(dir, base_filename)

    def profile_filename(self, base_filename, **kwargs):
        return self.generic_network_filename(base_filename, ext="csv", **kwargs)

    def assemble_output_directory(self, **kwargs):
        dir = self.__dir(kwargs.pop("network", Network.INVALID))
        dir_part = "".join(suffix_or_empty(val, sep='' if i == 0 else '_') for i, (_, val) in
                           enumerate(kwargs.items()))
        return join(dir, dir_part)
