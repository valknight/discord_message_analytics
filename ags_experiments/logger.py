import logging
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='agse.log', encoding='utf-8', mode='w')
formatter = logging.Formatter("[ %(asctime)s ] [ %(levelname)s ] %(message)s",
                              "%H:%M:%S %d-%m-%Y")
handler.setFormatter(formatter)
logger.addHandler(handler)
