from glob import glob
from os.path import join, exists

from pandas import read_excel, read_csv

from optimization_configuration.network.network_config_container import NetworkConfigContainer
from optimization_configuration.network.definitions import Network


class NetworkReader:
    filename = "Fogyasztok_*_SAP_adatokkal_kieg*"
    to_select = ["e_yearly_controlled", "e_yearly_residential", "e_yearly_commercial", "pv_power",
                 "e_yearly_consumption"]
    to_rename = {"nappali_fogy": "e_yearly_residential", "vezerelt_fogy": "e_yearly_controlled",
                 "teljesitmeny": "pv_power", "kisuzleti": "e_yearly_commercial"}

    def __init__(self, input_directory):
        self.input_directory = input_directory

    def clean_df(self, df):
        df = df.drop(df.columns[~df.columns.isin(self.to_select)], axis=1)
        df[df.isna()] = 0.0
        df = df.groupby(level=0).sum()
        df = df[~(df == 0).all(axis=1)]
        return df

    def read(self, network):
        try:
            file = glob(join(self.input_directory, str(network.value), self.filename))[0]
            df = read_excel(file, sheet_name=0, index_col=0, header=0).rename(columns=self.to_rename)
            return NetworkConfigContainer(network, households=self.clean_df(df))
        except IndexError:
            raise FileNotFoundError(
                f"File like '{self.filename}' not found in directory '{join(self.input_directory, f'{network.value}')}'")


class NetworkReaderForZNetwork(NetworkReader):
    consumer_filename = "consumers_clean.csv"
    consumption_filename = "measurements_clean.csv"
    id_filename = "ids.csv"
    to_select = ["e_yearly_residential", "e_yearly_controlled", "pv_power"]
    to_rename = {"Residential": "e_yearly_residential", "Controlled": "e_yearly_controlled",
                 "Commercial": "e_yearly_commercial", "PV": "pv_power", "HeatPump": "e_yearly_heat_pump",
                 "StreetLights": "e_yearly_streetlights"}

    def __init__(self, input_directory):
        super().__init__(input_directory)

    # Function to replace the only non-zero value in each row with a new number
    @staticmethod
    def replace_nonzero(row, new_number):
        row[row != 0] = new_number
        return row

    def read(self, network):
        assert network == Network.ZSOMBO, "Network must be Zsombo"

        consumers_file = join(self.input_directory, str(network.value), "from", self.consumer_filename)
        consumption_file = join(self.input_directory, str(network.value), "from", self.consumption_filename)
        identifier_file = join(self.input_directory, str(network.value), "from", self.id_filename)
        if not exists(consumers_file):
            raise FileNotFoundError(
                f"'{self.consumer_filename}' not found in directory '{join(self.input_directory, f'{network.value}')}'")
        if not exists(consumption_file):
            raise FileNotFoundError(
                f"'{self.consumption_filename}' not found in directory "
                f"'{join(self.input_directory, f'{network.value}')}'")

        consumption_df = read_csv(consumption_file, index_col=0, header=0)
        consumption_sum = consumption_df.sum(axis="rows")
        consumption_sum.index = consumption_sum.index.astype(int)
        # Consumer_id, Residential, Controlled, PV, HeatPump, Commercial, StreetLights
        df = read_csv(consumers_file, header=0, index_col=0, dtype=float).rename(columns=self.to_rename)
        df[self.to_select] = df[self.to_select].apply(
            lambda row: self.replace_nonzero(row, consumption_sum.loc[row.name]), axis=1)

        identifiers = read_csv(identifier_file, index_col=0, header=0, dtype={"MeterNo": str}).convert_dtypes().rename(
            columns={"Load type": "load_type"})
        df["Consumer_id"] = df.index
        df["MeterNo"] = df["Consumer_id"].apply(lambda x: identifiers.loc[x, "MeterNo"])
        df["e_yearly_consumption"] = df["e_yearly_residential"] + df["e_yearly_controlled"]
        return NetworkConfigContainer(network, households=self.clean_df(df.set_index("MeterNo")),
                                      measurements=consumption_df,
                                      identifiers=identifiers)
