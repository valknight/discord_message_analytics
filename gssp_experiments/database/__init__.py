import mysql.connector
import sys
from gssp_experiments.logger import logger
from gssp_experiments.settings.config import config

port = config['mysql'].get("port")
if port is None:
    logger.warn("'mysql'.'port' not found in config - defaulting to 3306")
    config['mysql']['port'] = 3306
try:
    cnx = mysql.connector.connect(**config['mysql'])
    logger.info("Created connection to MySQL")
except mysql.connector.errors.InterfaceError as exception:
    logger.error("{} - check your settings".format(exception))
    sys.exit(1)
cursor = cnx.cursor(buffered=True)
cursor_dict = cnx.cursor(dictionary=True)
