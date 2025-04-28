import struct
from   typing import Optional, Tuple

class Message:

    # Message IDs
    CHOKE             = 0
    UNCHOKE           = 1
    INTERESTED        = 2
    NOT_INTERESTED    = 3
    HAVE              = 4
    BITFIELD          = 5
    REQUEST           = 6
    PIECE             = 7
    CANCEL            = 8
    PORT              = 9
    
    @staticmethod
    def create_handshake(info_hash: bytes, peer_id: bytes) -> bytes:
        pstrlen  = bytes([19])  # BitTorrent protocol string length
        pstr     = b'BitTorrent protocol'
        reserved = bytes([0] * 8)  # Reserved bytes

        # Ensure info_hash and peer_id are byte sequences (this is important!)
        if not isinstance(info_hash, bytes):
            raise ValueError("info_hash must be bytes")
        if not isinstance(peer_id, bytes):
            raise ValueError("peer_id must be bytes")

        return pstrlen + pstr + reserved + info_hash + peer_id
    
    @staticmethod
    def parse_handshake(data: bytes) -> Optional[Tuple[bytes, bytes]]:
        if len(data) < 68:
            return None
            
        pstrlen = data[0]
        if pstrlen != 19:
            return None
            
        pstr = data[1:20]
        if pstr != b'BitTorrent protocol':
            return None
            
        # Extract info_hash and peer_id
        info_hash = data[28:48]
        peer_id   = data[48:68]
        
        return (info_hash, peer_id)
    
    @staticmethod
    def create_message(message_id: int, payload: bytes = b'') -> bytes:
        # Length prefix is message ID (1 byte) + payload length
        length = 1 + len(payload)
        return struct.pack('>I', length) + bytes([message_id]) + payload
    
    @staticmethod
    def create_keep_alive() -> bytes:
        return struct.pack('>I', 0)
    
    @staticmethod
    def create_interested() -> bytes:
        return Message.create_message(Message.INTERESTED)
    
    @staticmethod
    def create_not_interested() -> bytes:
        return Message.create_message(Message.NOT_INTERESTED)
    
    @staticmethod
    def create_choke() -> bytes:
        return Message.create_message(Message.CHOKE)
    
    @staticmethod
    def create_unchoke() -> bytes:
        return Message.create_message(Message.UNCHOKE)
    
    @staticmethod
    def create_have(piece_index: int) -> bytes:
        payload = struct.pack('>I', piece_index)
        return Message.create_message(Message.HAVE, payload)
    
    @staticmethod
    def create_request(index: int, begin: int, length: int) -> bytes:
        payload = struct.pack('>III', index, begin, length)
        return Message.create_message(Message.REQUEST, payload)
    
    @staticmethod
    def create_piece(index: int, begin: int, block: bytes) -> bytes:
        payload = struct.pack('>II', index, begin) + block
        return Message.create_message(Message.PIECE, payload)
    
    @staticmethod
    def create_cancel(index: int, begin: int, length: int) -> bytes:
        payload = struct.pack('>III', index, begin, length)
        return Message.create_message(Message.CANCEL, payload)
    
    @staticmethod
    def create_port(port: int) -> bytes:
        payload = struct.pack('>H', port)
        return Message.create_message(Message.PORT, payload)