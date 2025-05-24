from json import JSONEncoder
class APIResponse:
    file_type: str
    filename: str
    text: str

class APIResponseEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__