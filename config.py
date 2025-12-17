from dataclasses import dataclass


@dataclass
class AppConfig:
    datetime_format: str = "%Y-%m-%d %H:%M:%S"
    date_format: str = "%Y-%m-%d"
    auto_download_on_open: bool = False
    auto_download_interval_min: int = 5
    delete_after_download: bool = False


CONFIG = AppConfig()
