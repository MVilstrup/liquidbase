class LiquidError(Exception):
    pass


class BlobIDAlreadyExists(LiquidError):
    pass


class InvalidBlobValue(LiquidError):
    pass


class StoreIDAlreadyExists(LiquidError):
    pass
