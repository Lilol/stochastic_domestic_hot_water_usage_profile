from collections import defaultdict
from os.path import join

from yaml import safe_load, YAMLError

from utility.configuration import config


class element:
    """A base class for network elements."""
    def __init__(self):
        """Initializes a network element."""
        self.size = 0

    @classmethod
    def read(cls, yaml_contents):
        """Reads element data from YAML content."""
        this = cls()
        this.size = yaml_contents.pop("size")
        for key, item in yaml_contents.items():
            if key not in this.__dict__:
                print(f"Warning: network element '{key}' is missing from class dictionary")
            this.__dict__[key] = item
        return this

    def is_null(self):
        """Checks if the element is null."""
        return self.size == 0

    def to_dict(self):
        """Converts the element to a dictionary."""
        return {"size": self.size}


class element_with_profile(element):
    """A network element that has a profile."""
    def to_dict(self):
        """Converts the element to a dictionary."""
        dd = super().to_dict()
        dd["profile"] = f"{self.profile}"
        return dd


class pv(element_with_profile):
    """Represents a photovoltaic (PV) element."""
    def __init__(self):
        """Initializes a PV element."""
        super().__init__()
        self.profile = "PV"


class ue(element_with_profile):
    """Represents a user equipment (UE) element."""
    def __init__(self):
        """Initializes a UE element."""
        super().__init__()
        self.profile = "Residential"


class co(element_with_profile):
    """Represents a commercial element."""
    def __init__(self):
        """Initializes a commercial element."""
        super().__init__()
        self.profile = "Commercial"


class grid(element):
    """Represents a grid element."""
    def __init__(self):
        """Initializes a grid element."""
        super().__init__()
        self.size = 120
        self.p_with_max = 120
        self.p_inj_max = 120

    def to_dict(self):
        """Converts the element to a dictionary."""
        dd = super().to_dict()
        dd.update({"p_with_max": self.p_with_max, "p_inj_max": self.p_inj_max})
        return dd


class ut(element_with_profile):
    """Represents a utility element."""
    def __init__(self):
        """Initializes a utility element."""
        super().__init__()
        self.profile = "Controlled"


class boil(element_with_profile):
    """Represents a boiler element."""
    def __init__(self):
        """Initializes a boiler element."""
        super().__init__()


class name(element):
    """Represents a name element."""
    def __init__(self):
        """Initializes a name element."""
        super().__init__()
        del self.size
        self.name = "load"

    def is_null(self):
        """Checks if the element is null."""
        return False

    def to_dict(self):
        """Converts the element to a dictionary."""
        return {"name": self.name}


# Battery energy storage system (bess)
class bess(element):
    """Represents a battery energy storage system (BESS)."""
    def __init__(self):
        """Initializes a BESS element."""
        super().__init__()
        self.bess_params = {"eta_self_discharge": 1.0, "eta_bess_in": 0.98, "eta_bess_out": 0.96,
                            "eta_bess_stor": 0.995, "t_bess_min": 2, "soc_bess_min": 0.2, "soc_bess_max": 1,
                            "bess_size": 50.}

    def to_dict(self):
        """Converts the element to a dictionary."""
        dd = super().to_dict()
        dd.update(self.bess_params)
        return dd



class hss(element_with_profile):
    """Represents a domestic hot water system (HSS) element."""
    def __init__(self):
        """Initializes a HSS element."""
        super().__init__()
        self.profile = "dhw"
        self.hss_params = {"t_hss_min_in": 4, "t_hss_min_out": 1, "c_hss": 0.00116667, "a_hss": 0,
                           "T_env": config.getfloat("domestic_hot_water", "environment_temp"),
                           "T_max": config.getfloat("domestic_hot_water", "stored_water_temp") + 5,
                           "T_min": config.getfloat("domestic_hot_water", "cold_water_temp"),
                           "t_hss_in": config.getfloat("domestic_hot_water", "cold_water_temp"),
                           "T_set": config.getfloat("domestic_hot_water", "stored_water_temp"),
                           "T_out": config.getfloat("domestic_hot_water", "hot_water_temp"),
                           "T_in": config.getfloat("domestic_hot_water", "cold_water_temp"),
                           "eta_elh": config.getfloat("domestic_hot_water", "loss_coefficient"),
                           "vol_hss_water": 0.0,
                           "size_elh": 0.0}

    def reset(self):
        """Resets the HSS parameters."""
        self.hss_params["t_hss_min_in"] = 0  # minimum time of charge (hours)
        self.hss_params["a_hss"] = 0  # kW/°C, heat loss through surface
        self.hss_params["vol_hss_water"] = 0  # l/kg
        self.size = 0  # l/kg
        self.hss_params["size_elh"] = 0
        return self

    def __add__(self, other):
        """Adds two HSS elements together."""
        self.hss_params["t_hss_min_in"] = max(other.hss_params["t_hss_min_in"], self.hss_params["t_hss_min_in"])
        self.hss_params["a_hss"] += other.hss_params["a_hss"]
        self.hss_params["vol_hss_water"] += other.hss_params["vol_hss_water"]
        self.hss_params["size_elh"] += other.hss_params["size_elh"]
        self.size += other.size
        return self

    def to_dict(self):
        """Converts the element to a dictionary."""
        dd = super().to_dict()
        dd.update(self.hss_params)
        return dd


class UserPrototype:
    """A prototype for user configurations."""
    def __init__(self):
        """Initializes a user prototype."""
        self.data = {d.__class__.__name__: d for d in (grid(), bess(), ut(), boil(), ue(), co(), pv(), hss())}

    def __getitem__(self, item):
        """Gets a network element by its class name."""
        return self.data[item]

    @staticmethod
    def read(contents):
        """Reads user prototype data from contents."""
        this = UserPrototype()
        this.data = {}
        name = None
        for key, unit_contents in contents["units"].items():
            if key == "name":
                name = unit_contents["name"]
            else:
                this.data[key] = globals()[key].read()
        return this, name

    @property
    def bess_flag(self):
        """Checks if BESS is present in the user prototype."""
        return "bess" in self.data

    @property
    def pv_flag(self):
        """Checks if PV is present in the user prototype."""
        return "pv" in self.data

    @property
    def ut_flag(self):
        """Checks if utility element is present in the user prototype."""
        return "ut" in self.data

    @property
    def ue_flag(self):
        """Checks if residential user equipment is present in the user prototype."""
        return "ue" in self.data

    @property
    def co_flag(self):
        """Checks if commercial user equipment is present in the user prototype."""
        return "co" in self.data


class SimpleUserPrototype(UserPrototype):
    """A simplified user prototype with fewer elements."""
    def __init__(self):
        """Initializes a simple user prototype."""
        super().__init__()
        self.data = {d.__class__.__name__: d for d in (name(), bess(), ut(), ue(), co(), pv(), hss())}


class NetworkPrototype:
    """A prototype for network configurations."""
    def __init__(self):
        """Initializes a network prototype."""
        self.users = defaultdict(UserPrototype)

    def __iter__(self):
        """Iterates over the users in the network."""
        return iter(self.users.items())

    def __len__(self):
        """Gets the number of users in the network."""
        return len(self.users)

    @staticmethod
    def read(yaml_contents, path):
        """Reads network prototype data from YAML contents."""
        this = NetworkPrototype()
        for user in yaml_contents:
            user_file = join(path, f"{user}.yaml")
            with open(user_file, 'r') as file:
                try:
                    u_temp, user_name = UserPrototype.read(safe_load(file))
                    this.users[user_name] = u_temp
                except YAMLError as exc:
                    print(exc)
                    continue
        return this
