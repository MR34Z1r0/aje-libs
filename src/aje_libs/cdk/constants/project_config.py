from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from ..constants.environments import Environments  # Asegúrate de que la ruta es válida


@dataclass
class ProjectConfig:
    """Centralized project configurations"""
    account_id: str
    region_name: str
    enterprise: str
    project_name: str
    environment: Environments
    separator: str
    author: str
    app_config: Dict[Any, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, config: dict):
        try:
            environment = config.get("environment", "").upper()
            aws_environment = None         
            if environment == "PROD":
                aws_environment = Environments.PROD
            elif environment == 'TEST':
                aws_environment = Environments.TEST
            elif environment == 'DEV':
                aws_environment = Environments.DEV
            if not aws_environment:
                raise ValueError(f"Invalid environment: {environment}")
            
            return cls(
                account_id=config.get("account_id"),
                region_name=config.get("region_name"),
                enterprise=config.get("enterprise"),
                project_name=config.get("project_name"),
                environment=aws_environment,
                author=config.get("author"),
                separator=config.get("separator"),
                app_config=config.get("app_config")[environment.lower()]
            )
        except KeyError as e:
            raise ValueError(f"Missing required config key: {e}")
    
