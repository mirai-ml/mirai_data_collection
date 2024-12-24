"""
Implementation of the command line interface using Typer.
"""

import asyncio
from datetime import datetime, timedelta
from inspect import getfullargspec
from os import environ

import typer

from mcollect.core.config import config
from mcollect.core.logger import logger

from mcollect.api import (  # Assuming these functions are in the api module
    connect_to_mongo, data_collection, remove_older_data)

app = typer.Typer()

def main() -> None:
    """ Entry point for the CLI application. """
    app()

@app.callback()
def initialize(
    config_file: str = typer.Option("etc/config.toml", "-c", "--config", help="Path to the config file"),
    warn: str = typer.Option("WARNING", "-w", "--warn", help="Logger warning level")
):
    """ Initialize the application settings. """
    logger.start(warn)
    logger.debug("starting execution")
    config.load(config_file, params=environ)
    config.core.config = config_file
    config.core.logging = warn
    logger.stop()  # clear handlers to prevent duplicate records
    logger.start(config.core.logging)

@app.command()
def hello(name: str = typer.Option("World", "--name", "-n", help="Greeting name")):
    """ Print a simple greeting. """
    typer.echo(f"Hello, {name}!")

@app.command()
def forecast(
    model: str = typer.Option("fourcastnet2", help="Model name to run"),
    date: str = typer.Option((datetime.now() - timedelta(days=1)).strftime("%Y%m%d"), help="Date for the GRIB file [YYYYMMDD]"),
    time: int = typer.Option(12, help="Time for the GRIB file [HH]"),
    grib_file_path: str = typer.Option("./output_results.grib", help="Path to save the GRIB file"),
    lead_time: int = typer.Option(240, help="Lead time for the forecast [240h]")
):
    """ Run the data collection process for forecast. """
    args = locals()  # Get the function's arguments
    spec = getfullargspec(data_collection)
    
    if not spec.varkw:
        # Remove unexpected arguments if the function does not accept kwargs
        args = {key: args[key] for key in args if key in spec.args}
    
    try:
        # Check if data_collection is an async function and run it accordingly
        if asyncio.iscoroutinefunction(data_collection):
            asyncio.run(data_collection(**args))
        else:
            data_collection(**args)
    except RuntimeError as err:
        logger.critical(err)
        raise typer.Exit(code=1)
    
    logger.debug("successful completion")

@app.command()
def delete_old_data(
    date: str = typer.Option((datetime.now() - timedelta(days=30)).strftime("%Y%m%d"), help="Delete data older than this date [YYYYMMDD]"),
    collection_name: str = typer.Option("weather", help="Name of the MongoDB collection to clean")
):
    """ Remove all data older than the specified date from the MongoDB collection. """
    try:
        # Connect to MongoDB
        collection = asyncio.run(connect_to_mongo())
        
        # Remove data older than the specified date
        asyncio.run(remove_older_data(collection, date))
    except RuntimeError as err:
        logger.critical(err)
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"Error during data deletion: {e}")
        raise typer.Exit(code=1)

    logger.debug(f"Data older than {date} deleted from collection '{collection_name}'.")

if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        logger.error(repr(err))
        logger.critical("shutting down due to fatal error")
        raise
