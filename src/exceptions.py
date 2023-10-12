class DataclassJsonException(Exception):
    pass


class MalformedDataclassJson(DataclassJsonException):

    def __init__(self, data: dict):
        DataclassJsonException.__init__(self, data)
        self.data = data

    def __str__(self):
        return f"Unable to recreate a dataclass from f{self.data}"


class UnknownMessage(DataclassJsonException):
    def __init__(self, msg_type: str):
        self.data = msg_type

    def __str__(self):
        return (f"Message type {self.data} is not known for the recipient. "
                f"Make sure that you import the same version of API on both ends")
