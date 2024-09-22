#%%
import cfgrib

path = './output_results.grib'
#%%
X = cfgrib.open_datasets(path)
for  x in X:
    print(x.data_vars)
# %%
import xarray as xr

path = './output_results.grib'
# Load variables on the surface (without isobaricInhPa dimension)
ds_surface = xr.open_dataset(path, engine='cfgrib', backend_kwargs={'filter_by_keys': {'typeOfLevel': 'surface'}})
# print(ds_surface)
for a in ds_surface.data_vars.keys():
    print(a)    
print('----------------')
# Load variables on pressure levels (with isobaricInhPa dimension)
# ds_pressure = xr.open_dataset(path, engine='cfgrib', backend_kwargs={'filter_by_keys': {'typeOfLevel': 'isobaricInhPa'}})
# print(ds_pressure)

# print('----------------')
# # Merge the datasets manually
# ds_merged = xr.merge([ds_surface, ds_pressure])
# print(ds_merged)

# %%
import pygrib
path = './output_results.grib'
grib_file = pygrib.open(path)

#%%
# Iterate through the messages to get variable short names
for msg in grib_file:
    print(msg.shortName)

# Close the file
# grib_file.close()
print(grib_file)
# %%
print(grib_file.select(shortName='10u'))
# %%
