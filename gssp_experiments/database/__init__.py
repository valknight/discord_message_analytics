import mysql.connector
from gssp_experiments.logger import logger
from gssp_experiments.settings.config import config

port = config['mysql'].get("port")
if port is None:
    logger.warn("'mysql'.'port' not found in config - defaulting to 3306")
    config['mysql']['port'] = 3306
cnx = mysql.connector.connect(**config['mysql'])
cursor = cnx.cursor(buffered=True)
cursor_dict = cnx.cursor(dictionary=True)
