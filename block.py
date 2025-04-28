from   enum   import Enum

# Block Status Enum
class BlockStatus(Enum):
    REQUESTED        = 1
    DOWNLOADED       = 2
    NOT_REQUESTED    = 3

class Block:
    def __init__(self, index:  int, 
                       offset: int, 
                       length: int, data: bytes = b"", status: BlockStatus = BlockStatus.NOT_REQUESTED):
        
        self.index  = index        # Index of the piece this block belongs to
        self.offset = offset       # Offset within the piece
        self.length = length       # Length of the block
        self.data   = data         # The block data (or placeholder)
        self.status = status       # The status of the block (REQUESTED, DOWNLOADED, NOT_REQUESTED)

    def __repr__(self):
        return f"Block(piece_index={self.index}, offset={self.offset}, status={self.status.name})"
