import re
import unicodedata
from ..constants.services import Services
from ..constants.environments import Environments
from ..constants.project_config import ProjectConfig

class NameBuilder:
    """Standardized AWS resource name generator"""
        
    def __init__(self, project_config: ProjectConfig):
        self.project_config = project_config
    
    def __sanitize_name(self, name: str) -> str:
        """Alternative without unidecode"""
        normalized_name = unicodedata.normalize('NFKD', name.lower()).encode('ASCII', 'ignore').decode('ASCII')
        return re.sub(r"[., ]", "_", normalized_name)
    
    def build(self, service: Services, descriptive_name: str) -> str:
        """Generate a standardized resource name""" 
        components = []        
        if service == Services.S3_BUCKET:
            components = [
                self.project_config.enterprise,
                self.project_config.account_id,
                self.project_config.region_name,
                self.project_config.environment.value,
                self.project_config.project_name,
                descriptive_name,
                service.value
            ]
        else:
            components = [
                self.project_config.enterprise,
                self.project_config.environment.value,
                self.project_config.project_name,
                descriptive_name,
                service.value
            ]     
        name = self.project_config.separator.join(filter(None, components))
        return self.__sanitize_name(name)
    
    def build_dms_endpoint_name(self, descriptive_name: str, engine: str, endpoint_type) -> str:
        """Specialized naming for DMS endpoints"""
        type_str = "src" if endpoint_type.value == 1 else "tgt"
        base_name = self.build(Services.DMS_TASK, descriptive_name)
        return f"{base_name}-{engine}-{type_str}"