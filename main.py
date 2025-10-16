import logging

from config import ProjectConfig

projectConfig = ProjectConfig()

logging.basicConfig(
    level=projectConfig.log_level,
    filename=projectConfig.log_file,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    pass
