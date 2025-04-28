from   enum   import Enum

# Block Status Enum
class BlockStatus(Enum):
    REQUESTED        = 1
    DOWNLOADED       = 2
    NOT_REQUESTED    = 3

# Block Class to represent a single block of data
class Block:
    def __init__(self, piece_index: int, block_offset: int, length: int, block_data: bytes = b"", status: BlockStatus = BlockStatus.NOT_REQUESTED):
        self.piece_index  = piece_index        # Index of the piece this block belongs to
        self.block_offset = block_offset       # Offset within the piece
        self.block_length = length             # Length of the block
        self.block_data   = block_data         # The block data (or placeholder)
        self.status       = status             # The status of the block (REQUESTED, DOWNLOADED, NOT_REQUESTED)

    def __repr__(self):
        return f"Block(piece_index={self.piece_index}, offset={self.block_offset}, status={self.status.name})"
