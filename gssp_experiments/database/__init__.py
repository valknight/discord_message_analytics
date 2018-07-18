import mysql.connector

from gssp_experiments.settings.config import config

cnx = mysql.connector.connect(**config['mysql'])
cursor = cnx.cursor(buffered=True)
