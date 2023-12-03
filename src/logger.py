import logging

FORMAT = '[%(levelname)s] %(name)s %(asctime)s: %(message)s'

logging.basicConfig(format=FORMAT, level=logging.INFO)
OK_BLUE_LEVEL = 100
OK_CYAN_LEVEL = 101


class MyLogger(logging.getLoggerClass()):
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)

        logging.addLevelName(OK_BLUE_LEVEL, "OK_BLUE")
        logging.addLevelName(OK_CYAN_LEVEL, "OK_CYAN")

    def ok_blue(self, msg, *args, **kwargs):
        self._log(OK_BLUE_LEVEL, msg, args, **kwargs)

    def ok_cyan(self, msg, *args, **kwargs):
        self._log(OK_CYAN_LEVEL, msg, args, **kwargs)


class CustomFormatter(logging.Formatter):
    OK_GRAY = '\x1b[38;20m'
    HEADER = '\033[95m'
    OK_BLUE = '\033[94m'
    OK_CYAN = '\033[96m'
    OK_GREEN = '\033[92m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    END_C = '\033[0m'
    BOLD = '\033[1m'
    BOLD_RED = '\x1b[31;1m'
    UNDERLINE = '\033[4m'

    FORMATS = {
        logging.DEBUG: OK_GRAY + FORMAT + END_C,
        logging.INFO: OK_GREEN + FORMAT + END_C,
        logging.WARNING: WARNING + FORMAT + END_C,
        logging.ERROR: ERROR + FORMAT + END_C,
        logging.CRITICAL: BOLD_RED + FORMAT + END_C,
        OK_BLUE_LEVEL: OK_BLUE + FORMAT + END_C,
        OK_CYAN_LEVEL: OK_CYAN + FORMAT + END_C,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


logging.setLoggerClass(MyLogger)
root = logging.getLogger()

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())
root.handlers = [ch]
logger = logging.getLogger('sim_runner')
logger.handlers = []
