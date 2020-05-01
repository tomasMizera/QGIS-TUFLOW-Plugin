import os
import sys
from datetime import datetime
import re
import platform

try:
    import netCDF4
except ImportError:
    # TODO: This is not good, we need to add netCDF4 to OSGeo4W
    # and Mac packages !!!
    if platform.system() == 'Darwin':
        main_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.append(os.path.join(main_dir, "deps", platform.system()))
        import netCDF4

class NetCDFParticlesParser:
    def __init__(self):
        self.filename = None
        self.nc = None
        self.times = []
        self.timesteps_count = None

    def load_file(self, filename):
        self.filename = filename
        self.nc = netCDF4.Dataset(self.filename, 'r')
        if not self.is_valid_file():
            return False

        try:
            self._fill_times_arr()
        except KeyError:
            # probably some wrong file?
            self.nc = None

    def is_valid_file(self):
        if self.nc is None:
            return False

        variables = self.nc.variables.keys()
        mandatory_variables = ['x', 'y', 'z', 'Time', 'groupID']

        return all(must_var in variables for must_var in mandatory_variables)

    def get_all_variable_names(self):
        vars = list(self.nc.variables.keys())
        ignore_vars = ['Time', 'x', 'y', 'z']

        ret_vars = []
        for var in vars:
            if var in ignore_vars:
                continue

            var_dim = self.nc.variables[var].ndim
            if var_dim == 1 or var_dim == 2:
                ret_vars.append(var)
            if var_dim == 3:  # 3 dimensional variable, change to _x or _1 ..
                third_dimension_size = self.nc.variables[var].shape[2]
                if third_dimension_size == 1:
                    # variables with dimension time * trajectory * 1, so _x or _1 is unnecessary
                    ret_vars.append(var)
                elif third_dimension_size == 3 and var != 'mass':  # variables f.e. uvw, uvw_water
                    ret_vars.extend([var + '_x', var + '_y', var + '_z'])
                else:  # other variables, f.e. mass
                    for i in range(third_dimension_size):
                        ret_vars.append(var + '_' + str(i))

        return ret_vars

    def read_data_at_time(self, at_time):
        if self.nc is None:
            return None

        if at_time < 0 or at_time >= self.timesteps_count:
            return None
        ignored_vars = ['Time']

        data = {}
        variables = self.nc.variables.keys()
        for var in variables:
            if var in ignored_vars:  # if variable should be ignored, e.g. Time
                continue
            if self.nc.variables[var].ndim == 1:  # 1D variable
                data[var] = self.nc.variables[var][at_time].data  # TODO: repeat this value for num of particle times
            elif self.nc.variables[var].ndim == 2:  # 2D variable
                data[var] = self.nc.variables[var][at_time, :].data
            elif self.nc.variables[var].ndim == 3:  # 3D variable
                third_dimension_size = self.nc.variables[var].shape[2]
                if third_dimension_size == 1:
                    # variables with dimension time * trajectory * 1, so _x or _1 is unnecessary
                    data[var] = self.nc.variables[var][at_time, :, 0].data
                elif third_dimension_size == 3 and var != 'mass':  # variables f.e. uvw, uvw_water
                    data[var + '_x'] = self.nc.variables[var][at_time, :, 0].data
                    data[var + '_y'] = self.nc.variables[var][at_time, :, 1].data
                    data[var + '_z'] = self.nc.variables[var][at_time, :, 2].data
                else:  # other variables, f.e. mass
                    for i in range(third_dimension_size):
                        data[var + '_' + str(i)] = self.nc.variables[var][at_time, :, i].data
            else:
                pass  # unknown dimensions

        return data

    def get_timesteps_count(self):
        if not self.nc or not self.timesteps_count:
            return 0

        return self.timesteps_count

    def get_time_at(self, at_time):
        if at_time < 0 or at_time >= self.timesteps_count:
            return None
        if self.times is None:
            return at_time

        date = self.times[at_time].strftime('%Y-%m-%d')
        time = self.times[at_time].strftime('%H:%M:%S')
        return time, date

    def get_all_timedate_texts(self):
        timedateDict = {}
        timedateDict['time'] = []
        timedateDict['date'] = []

        for slide in range(self.timesteps_count):
            time, date = self.get_time_at(slide)
            timedateDict['time'].append(time)
            timedateDict['date'].append(date)

        return timedateDict

    def _build_time_string(self):
        self.time_string = None
        units = self.nc.variables['Time'].units
        name = self.nc.variables['Time'].long_name

        # string needs to be converted to format '<units> since <datetime>'
        time_tokens = name.split(' ')[-2:]
        if len(time_tokens) != 2:
            return None  # error

        conditions = [bool(re.match(re.compile('^[0-9]+'), candidate)) for candidate in time_tokens]
        if not (conditions[0] and conditions[1]):
            return None  # error

        # d/m/y needs to be converted to y-m-d
        date = ' '.join(time_tokens)
        date = datetime.strptime(date, '%d/%m/%Y %H:%M:%S')

        # needed format example: hours since 1950-01-01T00:00:00Z
        time_string = units + ' since ' + date.strftime('%Y-%m-%dT%H:%M:%SZ')

        self.time_string = time_string

    def _fill_times_arr(self):
        self._build_time_string()
        time_data = self.nc.variables['Time'][:].data
        self.timesteps_count = self.nc.variables['Time'].shape[0]

        if self.time_string is not None:
            self.times = netCDF4.num2date(time_data, units=self.time_string, calendar='gregorian')
