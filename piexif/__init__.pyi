from io import BytesIO
from typing import Any, Dict, List, Optional, Text, Tuple, Union

ImageInput = Union[str, bytes, Text]
FileName = Union[str, bytes, Text]
ExifDict = Dict[str, Any]
IFDs = List[Dict[str, Any]]
OutputFile = Optional[Union[str, bytes, Text, BytesIO]]
TagInfo = Dict[str, Union[str, int, Tuple[int, ...]]]

def load(
    input_data: ImageInput,
    key_is_name: bool = ...,
) -> ExifDict: ...
def load_bytes(data: bytes, key_is_name: bool = ...) -> ExifDict: ...
def load_file(filename: FileName, key_is_name: bool = ...) -> ExifDict: ...
def load_ifds(
    input_data: ImageInput,
    key_is_name: bool = ...,
    load_jpeg_data: bool = ...,
) -> IFDs: ...
def load_ifds_bytes(
    data: bytes,
    key_is_name: bool = ...,
    load_jpeg_data: bool = ...,
) -> IFDs: ...
def load_ifds_file(
    filename: FileName,
    key_is_name: bool = ...,
    load_jpeg_data: bool = ...,
) -> IFDs: ...
def dump(exif_dict: ExifDict) -> bytes: ...
def dump_ifds(ifds: IFDs) -> bytes: ...
def insert(exif: bytes, image: ImageInput, new_file: OutputFile = ...) -> None: ...
def insert_bytes(exif: bytes, data: bytes, new_file: OutputFile = ...) -> None: ...
def insert_file(
    exif: bytes, filename: FileName, new_file: OutputFile = ...
) -> None: ...
def remove(src: ImageInput, new_file: OutputFile = ...) -> None: ...
def remove_bytes(data: bytes, new_file: OutputFile = ...) -> None: ...
def remove_file(filename: FileName, new_file: OutputFile = ...) -> None: ...
def transplant(
    exif_src: ImageInput, image: ImageInput, new_file: OutputFile = ...
) -> None: ...
def transplant_bytes(
    exif_src: bytes, image: bytes, new_file: OutputFile = ...
) -> None: ...
def transplant_file(
    exif_src: FileName, image: FileName, new_file: OutputFile = ...
) -> None: ...

class _Types:
    Byte: int
    Ascii: int
    Short: int
    Long: int
    Rational: int
    SByte: int
    Undefined: int
    SShort: int
    SLong: int
    SRational: int
    Float: int
    DFloat: int
    Ifd: int

class _IFDConstants:
    def __getattr__(self, name: str) -> int: ...

TYPES: _Types
TAGS: Dict[str, Dict[int, TagInfo]]
ImageIFD: _IFDConstants
ExifIFD: _IFDConstants
GPSIFD: _IFDConstants
InteropIFD: _IFDConstants
VERSION: str

class _Config:
    allow_legacy_png_text_exif: bool

config: _Config

class InvalidImageDataError(ValueError): ...
class UnsupportedImageFormatError(InvalidImageDataError): ...
