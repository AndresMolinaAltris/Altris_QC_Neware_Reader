import logging.config
import os
import datetime
import yaml


def configure_logging(base_directory):

    try:
        log_dir = os.path.join(base_directory, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f'{log_dir}/Altris_QC_Neware_Reader_logging_{timestamp}.log'

        log_config_path = os.path.join(os.path.dirname(__file__), 'log_config.yaml')
        with open(log_config_path, 'rt') as f:
            config = yaml.safe_load(f.read())

        # Replace the placeholder with the actual filename
        config['handlers']['file']['filename'] = config['handlers']['file']['filename'].replace('LOG_FILENAME_PLACEHOLDER',
                                                                                            log_filename)
        logging.config.dictConfig(config)

        logging.debug("LOGGER-CONFIGURATOR. Logging configured successfully")

    except Exception as e:
        logging.error(f"LOGGER-CONFIGURATOR. An error occurred while configuring logging: {e}")