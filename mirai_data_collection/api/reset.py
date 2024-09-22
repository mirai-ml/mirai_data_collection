import typer
import motor.motor_asyncio
import asyncio
from datetime import datetime, timedelta

app = typer.Typer()

@app.callback()
def initialize(
    config_file: str = typer.Option("etc/config.toml", "-c", "--config", help="Path to the config file"),
    warn: str = typer.Option("WARNING", "-w", "--warn", help="Logger warning level")
):
    """ Initialize the application settings. """
    # config.load(config_file)
    # config.core.config = config_file
    # config.core.logging = warn

@app.command()
def hello(name: str = typer.Option("World", "--name", "-n", help="Greeting name")):
    """ Print a simple greeting. """
    typer.echo(f"Hello, {name}!")

async def drop_database(db_name='weather_data'):
    """
    Drop the specified database.
    """
    try:
        # Connect to the MongoDB client
        client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017/")
        
        # Drop the database
        await client.drop_database(db_name)
        
        print(f"Database '{db_name}' dropped successfully.")
        
    except Exception as e:
        print(f"Error dropping database '{db_name}': {str(e)}")
        raise  # Re-raise the exception after logging it

@app.command()
def reset(
    model: str = typer.Option("fourcastnet2", help="Model name to run"),
    date: str = typer.Option((datetime.now() - timedelta(days=1)).strftime("%Y%m%d"), help="Date for the GRIB file [YYYYMMDD]"),
    time: int = typer.Option(12, help="Time for the GRIB file [HH]"),
    grib_file_path: str = typer.Option("./output_results.grib", help="Path to save the GRIB file"),
    lead_time: int = typer.Option(240, help="Lead time for the forecast [240h]"),
    db_name: str = typer.Option("weather_data", help="Name of the database to reset")
):
    """
    Drops the specified database and re-runs the data collection process.
    """
    async def reset_and_collect_data():
        # Step 1: Drop the existing database
        await drop_database(db_name=db_name)

    asyncio.run(reset_and_collect_data())

if __name__ == "__main__":
    app()
