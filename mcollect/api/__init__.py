""" Application commands common to all interfaces.

"""
from .data_collect import data_collection, connect_to_mongo, remove_older_data


__all__ = "data_collection",
