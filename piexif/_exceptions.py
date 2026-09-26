class InvalidImageDataError(ValueError):
    pass


class UnsupportedImageFormatError(InvalidImageDataError):
    """The image signature identifies a format the operation cannot handle."""
