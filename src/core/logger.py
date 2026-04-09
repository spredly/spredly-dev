import logging

def get_module_logger(mod_name):
    """
    To use this:
        logger = get_module_logger(__name__, log_file="app.log")
    """
    logger = logging.getLogger(mod_name)
    logger.setLevel(logging.ERROR)

    if logger.handlers:
        return logger

    stream_handler = logging.StreamHandler()
    stream_formatter = logging.Formatter(
        "%(asctime)s [%(name)-6s] %(levelname)-8s %(message)s"
    )
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)

    return logger
