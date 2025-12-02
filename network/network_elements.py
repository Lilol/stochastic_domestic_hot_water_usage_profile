from collections import defaultdict
from os.path import join

from yaml import safe_load, YAMLError

from utility.configuration import config


class element:
    def __init__(self):
        self.size = 0

    @classmethod
    def read(cls, yaml_contents):
        this = cls()
        this.size = yaml_contents.pop("size")
        for key, item in yaml_contents.items():
            if key not in this.__dict__:
                print(f"Warning: network element '{key}' is missing from class dictionary")
            this.__dict__[key] = item
        return this

    def is_null(self):
        return self.size == 0

    def to_dict(self):
        return {"size": self.size}


class element_with_profile(element):
    def to_dict(self):
        dd = super().to_dict()
        dd["profile"] = f"{self.profile}"
        return dd


class pv(element_with_profile):
    def __init__(self):
        super().__init__()
        self.profile = "PV"


class ue(element_with_profile):
    def __init__(self):
        super().__init__()
        self.profile = "Residential"


class co(element_with_profile):
    def __init__(self):
        super().__init__()
        self.profile = "Commercial"


class grid(element):
    def __init__(self):
        super().__init__()
        self.size = 120
        self.p_with_max = 120
        self.p_inj_max = 120

    def to_dict(self):
        dd = super().to_dict()
        dd.update({"p_with_max": self.p_with_max, "p_inj_max": self.p_inj_max})
        return dd


class ut(element_with_profile):
    def __init__(self):
        super().__init__()
        self.profile = "Controlled"


class boil(element_with_profile):
    def __init__(self):
        super().__init__()


class name(element):
    def __init__(self):
        super().__init__()
        del self.size
        self.name = "load"

    def is_null(self):
        return False

    def to_dict(self):
        return {"name": self.name}


# Battery energy storage system (bess)
class bess(element):
    def __init__(self):
        super().__init__()
        self.bess_params = {"eta_self_discharge": 1.0, "eta_bess_in": 0.98, "eta_bess_out": 0.96,
                            "eta_bess_stor": 0.995, "t_bess_min": 2, "soc_bess_min": 0.2, "soc_bess_max": 1,
                            "bess_size": 50.}

    def to_dict(self):
        dd = super().to_dict()
        dd.update(self.bess_params)
        return dd



class hss(element_with_profile):
    def __init__(self):
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
        self.hss_params["t_hss_min_in"] = 0  # minimum time of charge (hours)
        self.hss_params["a_hss"] = 0  # kW/°C, heat loss through surface
        self.hss_params["vol_hss_water"] = 0  # l/kg
        self.size = 0  # l/kg
        self.hss_params["size_elh"] = 0
        return self

    def __add__(self, other):
        self.hss_params["t_hss_min_in"] = max(other.hss_params["t_hss_min_in"], self.hss_params["t_hss_min_in"])
        self.hss_params["a_hss"] += other.hss_params["a_hss"]
        self.hss_params["vol_hss_water"] += other.hss_params["vol_hss_water"]
        self.hss_params["size_elh"] += other.hss_params["size_elh"]
        self.size += other.size
        return self

    def to_dict(self):
        dd = super().to_dict()
        dd.update(self.hss_params)
        return dd


class UserPrototype:
    def __init__(self):
        self.data = {d.__class__.__name__: d for d in (grid(), bess(), ut(), boil(), ue(), co(), pv(), hss())}

    def __getitem__(self, item):
        return self.data[item]

    @staticmethod
    def read(contents):
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
        return "bess" in self.data

    @property
    def pv_flag(self):
        return "pv" in self.data

    @property
    def ut_flag(self):
        return "ut" in self.data

    @property
    def ue_flag(self):
        return "ue" in self.data

    @property
    def co_flag(self):
        return "co" in self.data


class SimpleUserPrototype(UserPrototype):
    def __init__(self):
        super().__init__()
        self.data = {d.__class__.__name__: d for d in (name(), bess(), ut(), ue(), co(), pv(), hss())}


class NetworkPrototype:
    def __init__(self):
        self.users = defaultdict(UserPrototype)

    def __iter__(self):
        return iter(self.users.items())

    def __len__(self):
        return len(self.users)

    @staticmethod
    def read(yaml_contents, path):
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
