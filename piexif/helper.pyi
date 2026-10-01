from typing import Text, Tuple

class UserComment:
    ASCII: str
    JIS: str
    UNICODE: str
    ENCODINGS: Tuple[str, str, str]
    @classmethod
    def load(cls, data: bytes) -> Text: ...
    @classmethod
    def dump(cls, data: Text, encoding: str = ...) -> bytes: ...
