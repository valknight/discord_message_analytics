import Algorithmia

from gssp_experiments.settings.config import config

algo_client = Algorithmia.client(config['algorithmia_key'])
