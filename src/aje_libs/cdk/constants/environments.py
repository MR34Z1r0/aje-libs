from enum import Enum

class Environments(Enum):
    """Environment identifiers for resource naming and tagging"""
    DEV = "DEV"
    TEST = "TEST"
    PROD = "PROD"