import os

from pydantic_settings import BaseSettings


class Setting(BaseSettings):
    name: str = str(os.environ.get("APP_NAME", "MaptoMethod"))
    contact_name: str = str(os.environ.get("ADMIN_NAME", "MapToMethod Admin"))
    admin_email: str = str(os.environ.get("ADMIN_MAIL", "maptomethod@matolab.org"))
    items_per_user: int = 50
    version: str = str(os.environ.get("APP_VERSION", "v1.1.1"))
    config_name: str = str(os.environ.get("APP_MODE", "development"))
    openapi_url: str = "/api/openapi.json"
    docs_url: str = "/api/docs"
    source: str = str(
        os.environ.get("APP_SOURCE", "https://github.com/Mat-O-Lab/MapToMethod")
    )
    desc: str = "Tool to map content of JSON-LD douments (for example output of [CSVtoCSVW](https://github.com/Mat-O-Lab/CSVToCSVW) to Entities in knowledge graphs by creating mapping rules with conditions in [YARRRML](https://rml.io/yarrrml) format."
    org_site: str = "https://mat-o-lab.github.io/OrgSite"
