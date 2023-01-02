from enum import Enum

# File    : GeneratorTypes.py
# Classes : GeneratorTypes
# Author  : Adam Biggs (100197567)
# Date    : 18/05/2022
# Notes   : An enum used by gui.py to run dungeonify.py's generate method using a switch statement.


class GeneratorTypes(Enum):
    selectedBuildings = 0
    rotatedBuildings = 1
    repositionedBuildings = 2
    dungeonifiedBuildings = 3
