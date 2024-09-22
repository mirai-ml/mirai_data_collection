from pymongo import ASCENDING, GEOSPHERE

from ..core.logger import logger  # Ensure logger is configured properly elsewhere
import os
import pygrib
import motor.motor_asyncio
from datetime import datetime
import asyncio
from openforecast import execute_model
from openforecast.model.fourcastnet import Fourcastnet0ModelVars, Fourcastnet1ModelVars, Fourcastnet2ModelVars

def run_model_and_generate_grib(model='fourcastnet2', date=None, grib_file_path='./output_results.grib', time=None, lead_time=240):
    """
    Generate a GRIB file using the specified model and parameters.
    
    Args:
        model (str): The model to use.
        date (str): The date for which to generate data.
        grib_file_path (str): The path where the GRIB file will be saved.
        time (str): The time for which to generate data.
        lead_time (int): Lead time in hours for the forecast.

    Raises:
        Exception: If the GRIB file is not generated successfully.
    """
    try:
        print(f"Generating GRIB file at {grib_file_path}...")
        execute_model(
            model=model,
            path=grib_file_path,
            date=date,
            time=time,
            lead_time=lead_time
        )
        if os.path.exists(grib_file_path):
            print(f"GRIB file successfully generated at {grib_file_path}.")
        else:
            raise FileNotFoundError(f"GRIB file was not created at {grib_file_path}.")
    except Exception as e:
        print(f"Error during GRIB file generation: {str(e)}")
        raise

async def connect_to_mongo():
    """
    Asynchronously connect to MongoDB and create necessary indexes.

    Returns:
        collection: The MongoDB collection object for weather data.
    """
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017/")
        db = client.weather_data  # Database name
        collection = db.weather
        await collection.create_index([("location", GEOSPHERE)])
        await collection.create_index([("timestamp", ASCENDING)])
        await collection.create_index([("variables.shortName", ASCENDING)])
        await collection.create_index([("pressureLevel", ASCENDING)])
        print("Connected to MongoDB and indexes created.")
        return collection
    except Exception as e:
        print(f"Error connecting to MongoDB: {str(e)}")
        raise

def validate_coordinates(lon, lat):
    """
    Adjust and validate coordinates.

    Args:
        lon (float): Longitude value.
        lat (float): Latitude value.

    Returns:
        tuple: Adjusted (lon, lat) tuple.
    """
    if not (0 <= lon <= 360):
        raise ValueError(f"Invalid longitude value: {lon}. It should be between 0 and 360.")
    
    lon = (lon + 180) % 360 - 180  # Convert to [-180, 180] range
    lat = max(min(lat, 90), -90)   # Cap latitude between -90 and 90
    return lon, lat

async def parse_grib_and_store_in_mongo(grib_file_path, collection, model_parameters):
    """
    Parse the GRIB file and insert data into MongoDB.

    Args:
        grib_file_path (str): Path to the GRIB file.
        collection: MongoDB collection where data will be stored.
    """
    try:
        print('fglkdfgjdfkg')    
        
        grbs = pygrib.open(grib_file_path)
        print('sd;flsdkf')
        print(f"Parsing GRIB file: {grib_file_path}")

        for grb in grbs:
            latitudes, longitudes = grb.latlons()
            timestamp = datetime.strptime(str(grb.dataDate), '%Y%m%d')
            pressure_level = getattr(grb, 'level', None)

            tasks = []
            for lat, lon, value in zip(latitudes.flat, longitudes.flat, grb.values.flat):
                lon, lat = validate_coordinates(lon, lat)
                
                document = {
                    "timestamp": timestamp,
                    "forecastTime": grb.forecastTime,
                    "pressureLevel": pressure_level,
                    "location": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    },
                    "variables": {
                        grb.shortName: value  # Use grb.shortName for the variable name
                    }
                }
                tasks.append(collection.insert_one(document))
            await asyncio.gather(*tasks)

        print("Data successfully inserted into MongoDB.")
    except Exception as e:
        print(f"Error parsing GRIB file or inserting data into MongoDB: {str(e)}")
        raise

async def drop_collection(collection_name):
    """
    Drop the specified collection from the MongoDB database.

    Args:
        collection_name (str): The name of the collection to drop.

    Raises:
        Exception: If there is an issue dropping the collection.
    """
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017/")
        db = client.weather_data  # Database name
        await db.drop_collection(collection_name)
        print(f"Collection '{collection_name}' has been dropped successfully.")
    except Exception as e:
        print(f"Error dropping collection '{collection_name}': {str(e)}")
        raise

async def remove_older_data(collection, date_str):
    """
    Remove all documents from the collection with a timestamp older than the given date.

    Args:
        collection: MongoDB collection from which data will be removed.
        date_str (str): Date in the format 'YYYYMMDD'. All data older than this date will be removed.

    Raises:
        Exception: If there is an issue deleting the data.
    """
    try:
        # Convert the date string in 'YYYYMMDD' format to a datetime object
        date = datetime.strptime(date_str, '%Y%m%d')
        # Remove all documents with a timestamp less than the specified date
        result = await collection.delete_many({"timestamp": {"$lt": date}})
        print(f"Deleted {result.deleted_count} documents older than {date_str}.")
    except Exception as e:
        print(f"Error removing older data: {str(e)}")
        raise


def get_parameters(model='fourcastnet2'):
    """
    Get the model parameters based on the specified model.

    Args:
        model (str): The model name.

    Returns:
        ModelVars: The model variables object for the specified model.
    """
    if model == 'fourcastnet1':
        return Fourcastnet1ModelVars()
    elif model == 'fourcastnet2':
        return Fourcastnet2ModelVars()
    elif model == 'fourcastnet0':
        return Fourcastnet0ModelVars()
    else:
        raise ValueError(f"Unrecognized model name {model}")

async def data_collection(model='fourcastnet2', date=None, grib_file_path='./output_results.grib', time=None, lead_time=240):
    """
    Main function to generate GRIB file, connect to MongoDB, and store parsed data.

    Args:
        model (str): The model name to use for generating the GRIB file.
        date (str): The date for which to generate data.
        grib_file_path (str): The path to save the generated GRIB file.
        time (str): The time for which to generate data.
        lead_time (int): Lead time in hours for the forecast.
    """
    logger.debug("Executing main command")
    try:
        model_parameters = get_parameters(model=model)
    except Exception as e:
        print(f"Error getting model parameters: {str(e)}")
        return

    # Run the model and generate the GRIB file
    run_model_and_generate_grib(model=model, date=date, grib_file_path=grib_file_path, time=time, lead_time=lead_time)
    try:
        collection = await connect_to_mongo()
    except Exception as e:
        print(f"Error connecting to MongoDB: {str(e)}")
        
    await parse_grib_and_store_in_mongo(grib_file_path, collection, model_parameters)

