import os
from typing import Any
import json
import requests


# Custom modules
from .utils import smart_json_load


# Set some constants
BASE_URL: str = "https://enka.network/api/uid"
CACHE_FOLDER: str = os.path.join("cache")
CONSTANTS_FOLDER: str = os.path.join("src", "constants")


# Load some other constants
CHARACTERS: dict[Any, Any] = smart_json_load(
    url="https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/characters.json",
    cache_folder=CONSTANTS_FOLDER,
)
LOC: dict[Any, Any] = smart_json_load(
    url="https://raw.githubusercontent.com/EnkaNetwork/API-docs/refs/heads/master/store/loc.json",
    cache_folder=CONSTANTS_FOLDER,
)
RELIQUARIAFFIXEXCELCONFIGDATA: list[dict[str, Any]] = smart_json_load(
    url="https://gitlab.com/Dimbreath/AnimeGameData/-/raw/master/ExcelBinOutput/ReliquaryAffixExcelConfigData.json",
    cache_folder=CONSTANTS_FOLDER,
)
