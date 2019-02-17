import Algorithmia

from ags_experiments.settings.config import config

algo_client = Algorithmia.client(config['algorithmia_key'])
