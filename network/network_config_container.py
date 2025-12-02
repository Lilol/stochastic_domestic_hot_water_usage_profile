from pandas import Index, to_datetime

from utility.configuration import config

load_type = {
    "pv": 4,
    "controlled": 3,
    "residential": 2
}


class NetworkConfigContainer:
    """A container for network configuration data."""
    def __init__(self, nw, identifiers=None, households=None, measurements=None):
        """Initializes the NetworkConfigContainer with network data."""
        self.nw = nw
        self.identifiers = identifiers
        self.households = households
        self.measurements = measurements
        self.measurements.index = to_datetime(self.measurements.index)
        resolution = config.get("time", "resolution")
        self.measurements = self.measurements.resample(resolution).sum()

    def __get_consumer(self, load_type):
        """Gets consumer indices for a given load type."""
        return self.identifiers[self.identifiers.load_type == load_type].index

    def convert_identifier_type(self, new_type):
        """Converts the data type of identifiers."""
        self.identifiers.index = self.identifiers.index.astype(new_type)
        self.measurements.columns = self.measurements.columns.astype(new_type)

    def get_pvs(self):
        """Gets the indices of PVs."""
        return self.__get_consumer(4)

    def get_controlled(self):
        """Gets the indices of controlled loads."""
        return self.__get_consumer(3)

    def get_residential(self):
        """Gets the indices of residential loads."""
        return self.__get_consumer(2)

    def get_measurement_id(self, metering_id, load_type):
        """Gets the measurement ID for a given metering ID and load type."""
        try:
            return self.identifiers[
                (self.identifiers.load_type == load_type) & (self.identifiers.MeterNo == metering_id)].index[0]
        except KeyError:
            return None

    def get_measurement_id_pv(self, metering_id):
        """Gets the measurement ID for a PV load."""
        return self.get_measurement_id(metering_id, load_type["pv"])

    def get_measurement_id_controlled(self, metering_id):
        """Gets the measurement ID for a controlled load."""
        return self.get_measurement_id(metering_id, load_type["controlled"])

    def get_measurement_id_residential(self, metering_id):
        """Gets the measurement ID for a residential load."""
        return self.get_measurement_id(metering_id, load_type["residential"])

    def get_consumption(self):
        """Gets the indices of all consumption loads."""
        return Index.union(self.get_residential(), self.get_controlled())

    def get_measurement(self, metering_id, load_type):
        """Gets the measurement series for a given metering ID and load type."""
        id = self.get_measurement_id(metering_id, load_type)
        return self.measurements[id]
