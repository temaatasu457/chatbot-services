import logging

documents_logger = logging.getLogger('documents')
documents_logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("documents_db_logs.log")
stream_handler = logging.StreamHandler()

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

documents_logger.addHandler(file_handler)
documents_logger.addHandler(stream_handler)