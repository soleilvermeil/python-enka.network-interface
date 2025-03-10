import os
import json
import requests
import datetime as dt
import logging


# Custom modules
from ..types import *
from ..utils.general import nested_get
from ..constants.general import LANG, PLAYERS_CACHE_FOLDER, PLAYER_CACHE_EXPIRATION
from ..constants.enka import BASE_URL, CHARACTERS, LOC, RELIQUARIAFFIXEXCELCONFIGDATA, RESPONSE_CODES



def prop_id_to_artifact_stat(prop_id: str) -> StatModifier:
    """
    Convert a property ID to an artifact stat.
    """
    match prop_id:
        case "FIGHT_PROP_BASE_ATTACK":
            raise ValueError(f"Main stat {prop_id} is not valid for an artifact.")
        case "FIGHT_PROP_HP":
            return StatModifier.HP_FLAT
        case "FIGHT_PROP_HP_PERCENT":
            return StatModifier.HP_PERCENT
        case "FIGHT_PROP_ATTACK":
            return StatModifier.ATK_FLAT
        case "FIGHT_PROP_ATTACK_PERCENT":
            return StatModifier.ATK_PERCENT
        case "FIGHT_PROP_DEFENSE":
            return StatModifier.DEF_FLAT
        case "FIGHT_PROP_DEFENSE_PERCENT":
            return StatModifier.DEF_PERCENT
        case "FIGHT_PROP_CRITICAL":
            return StatModifier.CR
        case "FIGHT_PROP_CRITICAL_HURT":
            return StatModifier.CD
        case "FIGHT_PROP_CHARGE_EFFICIENCY":
            return StatModifier.ER
        case "FIGHT_PROP_ELEMENT_MASTERY":
            return StatModifier.EM
        case "FIGHT_PROP_HEAL_ADD":
            return StatModifier.HealingBonus
        case "FIGHT_PROP_PHYSICAL_ADD_HURT":
            return StatModifier.DMG_Physical
        case "FIGHT_PROP_FIRE_ADD_HURT":
            return StatModifier.DMG_Fire
        case "FIGHT_PROP_ELEC_ADD_HURT":
            return StatModifier.DMG_Electro
        case "FIGHT_PROP_WATER_ADD_HURT":
            return StatModifier.DMG_Hydro
        case "FIGHT_PROP_WIND_ADD_HURT":
            return StatModifier.DMG_Anemo
        case "FIGHT_PROP_ICE_ADD_HURT":
            return StatModifier.DMG_Cryo
        case "FIGHT_PROP_ROCK_ADD_HURT":
            return StatModifier.DMG_Geo
        case "FIGHT_PROP_GRASS_ADD_HURT":
            return StatModifier.DMG_Dendro
        case _:
            raise ValueError(f"Invalid property ID {prop_id}.")


def get_artifact_rolls(
    artifact_dict: ArtifactDict,
) -> list[tuple[StatModifier, float]]:
    """
    Get the rolls of an artifact. The rolls are a list of tuples.
    First element of each tuple is the type of the roll, and the second
    element is its value.
    """
    # Initialize the list of rolls
    rolls: list[tuple[StatModifier, float]] = []

    # Get all the roll IDs of the artifact
    roll_ids: list[int] = nested_get(artifact_dict, "reliquary", "appendPropIdList")

    # For each ID, get the corresponding stat and value
    for roll_id in roll_ids:
        for element in RELIQUARIAFFIXEXCELCONFIGDATA:
            if element["id"] == roll_id:
                roll_type: StatModifier = prop_id_to_artifact_stat(element["propType"])
                roll_value: float = element["propValue"]
                rolls.append((roll_type, roll_value))

    # Return the list of rolls
    return rolls


def get_artifact_main_stat(
    artifact_dict: ArtifactDict,
) -> tuple[StatModifier, float]:
    """
    Get the main stat of an artifact. The main stat is a tuple composed of
    the type of the main stat and its value.
    """
    # Get the main stat raw data
    main_stat_id: str = nested_get(artifact_dict, "flat", "reliquaryMainstat", "mainPropId")
    main_stat_value: float = nested_get(artifact_dict, "flat", "reliquaryMainstat", "statValue")

    # Find the corresponding main stat type
    main_stat_type: StatModifier = prop_id_to_artifact_stat(main_stat_id)

    # Adjust the value if it is a percentage
    if main_stat_type in PERCENT_STAT_MODIFIERS:
        main_stat_value /= 100

    # Return the main stat type and its value
    return main_stat_type, main_stat_value


def get_artifact_substats(
    artifact_dict: ArtifactDict,
) -> list[tuple[StatModifier, float]]:
    """
    Get the substats of an artifact. The substats are a list of tuples.
    First element of each tuple is the type of the substat, and the second
    element is its value.
    """
    # Get all the substats of the artifact
    substat_dicts: list[SubstatDict] = nested_get(artifact_dict, "flat", "reliquarySubstats")

    # Initialize the list of substats
    substats: list[tuple[StatModifier, float]] = []
    for substat_dict in substat_dicts:

        # Find the raw data of the substat
        substat_id = nested_get(substat_dict, "appendPropId")
        substat_value: float = nested_get(substat_dict, "statValue")

        # Find the corresponding substat type
        substat_type: StatModifier = prop_id_to_artifact_stat(substat_id)

        # Adjust the value if it is a percentage
        if substat_type in PERCENT_STAT_MODIFIERS:
            substat_value /= 100

        # Append the substat to the list
        substats.append((substat_type, substat_value))

    # Return the list of substats
    return substats


def get_character_name(character_dict: CharacterDict) -> str:
    """
    Get the name of a character from its dictionary.
    """
    # Get the character ID
    character_id: int = nested_get(character_dict, "avatarId")

    # Get the character name hash from its ID
    character_name_hash: int = nested_get(
        CHARACTERS,
        str(character_id),
        "NameTextMapHash"
    )

    # Get a human-readable name from the hash, in the desired language
    character_name: str = nested_get(
        LOC,
        LANG,
        str(character_name_hash),
    )

    # Return the character name
    return character_name


def get_artifact_level(artifact_dict: ArtifactDict) -> int:
    """
    Get the level of an artifact.
    """
    return nested_get(artifact_dict, "reliquary", "level")


def get_player_nickname(player_dict: PlayerDict) -> str:
    """
    Get the nickname of a player.
    """
    return nested_get(player_dict, "playerInfo", "nickname")


def get_character_stat(
    character_dict: CharacterDict,
    stat: Stat,
) -> float:
    # Compute the wanted stat
    match stat:
        case Stat.HP:
            hp_base: float = nested_get(character_dict, "fightPropMap").get("1", 0)
            hp_flat: float = nested_get(character_dict, "fightPropMap").get("2", 0)
            hp_percent: float = nested_get(character_dict, "fightPropMap").get("3", 0)
            return hp_base * (1 + hp_percent) + hp_flat
        case Stat.ATK:
            atk_base: float = nested_get(character_dict, "fightPropMap").get("4", 0)
            atk_flat: float = nested_get(character_dict, "fightPropMap").get("5", 0)
            atk_percent: float = nested_get(character_dict, "fightPropMap").get("6", 0)
            return atk_base * (1 + atk_percent) + atk_flat
        case Stat.DEF:
            def_base: float = nested_get(character_dict, "fightPropMap").get("7", 0)
            def_flat: float = nested_get(character_dict, "fightPropMap").get("8", 0)
            def_percent: float = nested_get(character_dict, "fightPropMap").get("9", 0)
            return def_base * (1 + def_percent) + def_flat
        case Stat.CR:
            return nested_get(character_dict, "fightPropMap").get("20", 0)
        case Stat.CD:
            return nested_get(character_dict, "fightPropMap").get("22", 0)
        case Stat.ER:
            return nested_get(character_dict, "fightPropMap").get("23", 0)
        case Stat.EM:
            return nested_get(character_dict, "fightPropMap").get("28", 0)
        case _:
            raise ValueError(f"Invalid stat {stat}.")


def get_character_weapon(
    character_dict: CharacterDict,
) -> WeaponDict:
    """
    Get the weapon of a character.
    """
    # Get all the equipped dicts
    equip_dicts: list[EquipmentDict] = nested_get(character_dict, "equipList")

    # Keep only weapon, characterized by having a 'weapon' key
    weapon_dict: list[WeaponDict] = [
        equip_dict for equip_dict in equip_dicts
        if nested_get(equip_dict, "weapon") is not None
    ]

    # Check that there is exactly one weapon, and return it
    if len(weapon_dict) != 1:
        raise ValueError(f"Expected one weapon, got {len(weapon_dict)}.")
    return weapon_dict[0]


def get_artifact_type(artifact_dict: ArtifactDict) -> ArtifactType:
    # Get the equip type
    equip_type: str = nested_get(artifact_dict, "flat", "equipType")

    # Find the corresponding artifact type
    match equip_type:
        case "EQUIP_BRACER":
            return ArtifactType.FLOWER
        case "EQUIP_NECKLACE":
            return ArtifactType.PLUME
        case "EQUIP_SHOES":
            return ArtifactType.SANDS
        case "EQUIP_RING":
            return ArtifactType.GOBLET
        case "EQUIP_DRESS":
            return ArtifactType.CIRCLET
        case _:
            raise ValueError(f"Invalid equip type {equip_type}.")


def get_character_artifact(
    character_dict: CharacterDict,
    artifact_type: ArtifactType,
) -> ArtifactDict | None:
    """
    Get the artifact of a specific type from a character. If no artifact of
    the specified type is found, None is returned.
    """
    # Get all the equipped dicts
    equip_dicts: list[EquipmentDict] = nested_get(character_dict, "equipList")

    # Keep only artifacts, characterized by having a 'reliquary' key
    artifact_dicts: list[ArtifactDict] = [
        equip_dict for equip_dict in equip_dicts
        if nested_get(equip_dict, "reliquary") is not None
    ]

    # Determine the type of each artifact
    artifact_types: list[ArtifactType] = [
        get_artifact_type(artifact_dict=artifact_dict)
        for artifact_dict in artifact_dicts
    ]

    # Return the artifact dict corresponding to the wanted type
    if artifact_type not in artifact_types:
        return None
    type_index: int = artifact_types.index(artifact_type)
    return artifact_dicts[type_index]


def get_player_dict(
        uid: int,
        summary_only: bool = False,
        allow_file_cache: bool = True,
    ) -> PlayerDict:
        """
        Get the informations from Enka.Network API.

        Args:
            uid (int): the UID of the player.
            summary_only (bool): if True, only the summary is returned.
            allow_file_cache (bool): if True, the data is saved to a file.

        Returns:
            data (PlayerDict): the data of the player.

        Raises:
            requests.HTTPError: if the Enka.Network API returns an error.
            Exception: if the request failed for an unexpected reason (which
                is not related to the Enka.Network API).
        """
        # If 'allow_file_cache' is True, check if the file exists
        file_path: str = os.path.join(PLAYERS_CACHE_FOLDER, f"{uid}.json")

        # Check if the file exists, and load it if it does
        if allow_file_cache and os.path.exists(file_path):

            # Get the last modification date of the file
            timestamp: float = os.path.getmtime(file_path)
            last_modification: dt.datetime = dt.datetime.fromtimestamp(timestamp)

            # Retrieve file from cache only if it is less than 1 day old
            if dt.datetime.now() - last_modification < PLAYER_CACHE_EXPIRATION:
                logging.debug(f"Using cache for player {uid}.")
                try:
                    with open(file_path, "r") as file:
                        return json.load(file)
                except json.JSONDecodeError:
                    logging.error(f"Could not read cache for player {uid}. Fetching new data.")
            else:
                logging.debug(f"Cache for player {uid} is outdated. Fetching new data.")

        # Define the type for future variables
        response: requests.Response
        data: PlayerDict

        # If summary_only is False, return the full data. Otherwise, only
        # return a summary
        if not summary_only:
            response = requests.get(f"{BASE_URL}/{uid}")
        else:
            response = requests.get(f"{BASE_URL}/{uid}?info")

        # Check the status code of the response
        if response.status_code in RESPONSE_CODES:
            raise requests.HTTPError(RESPONSE_CODES[response.status_code])
        elif response.status_code != 200:
            raise Exception(f"Unexpected status code {response.status_code}.")
        else:
            data = response.json()

        # If 'allow_file_cache' is True, save the data to the file
        if allow_file_cache:
            os.makedirs(PLAYERS_CACHE_FOLDER, exist_ok=True)
            with open(file_path, "w") as file:
                json.dump(data, file)

        # Return the data
        return data
