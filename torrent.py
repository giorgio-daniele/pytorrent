import os
import hashlib
import bencodepy

class Torrent:

    def __init__(self, data: dict):
        self.data           = data
        self.info           = data[b'info']
        self.info_hash      = self._calculate_info_hash()
        self.announce_url   = data[b'announce'].decode('utf-8')
        self.piece_length   = self.info[b'piece length']
        self.pieces         = self.info[b'pieces']
        
        # Set name
        self.name = self.info[b'name'].decode('utf-8')
        
        # Calculate total size
        if b'length' in self.info:
            # Single file torrent
            self.size           = self.info[b'length']
            self.files            = [{'path': self.name, 'length': self.size}]
            self.is_single_file   = True
        else:
            # Multi-file torrent
            self.files = []
            self.size  = 0
            for file_dict in self.info[b'files']:
                parts     = [part.decode('utf-8') for part in file_dict[b'path']]
                file_name = os.path.join(self.name, *parts)
                file_size = file_dict[b'length']
                self.files.append({'path': file_name, 'length': file_size})
                self.size += file_size
            self.is_single_file = False
            
        # Calculate number of pieces
        self.num_pieces = len(self.pieces) // 20
    
    def _calculate_info_hash(self) -> bytes:
        return hashlib.sha1(bencodepy.encode(self.info)).digest()
    
    @classmethod
    def from_file(cls, file_name: str):
        try:
            with open(file_name, 'rb') as f:
                data = f.read()
            decoded_data = bencodepy.decode(data)
            return cls(decoded_data)
        except (IOError, bencodepy.DecodingError) as e:
            raise ValueError(f"Error reading torrent file: {e}")
        
    def human_readable_size(self, size_in_bytes):
        for unit in ['bytes', 'KB', 'MB', 'GB', 'TB']:
            if size_in_bytes < 1024.0:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024.0

    def debug_print(self):
        print("\033[1;34mTorrent Debug Information:\033[0m")
        print(f"\033[1;32m  Torrent Name:\033[0m {self.name}")
        print(f"\033[1;32m  Announce URL:\033[0m {self.announce_url}")
        print(f"\033[1;32m  Torrent Hash:\033[0m \033[1;35m{self.info_hash.hex()}\033[0m")
        print(f"\033[1;32m  Piece Length:\033[0m {self.human_readable_size(self.piece_length)}")
        print(f"\033[1;32m  Total Pieces:\033[0m {self.num_pieces}")
        print(f"\033[1;32m  Total Size:\033[0m {self.human_readable_size(self.size)}")
        
        print(f"\033[1;32m  Files:\033[0m")
        print(f"\033[1;32m  Files Count:\033[0m {len(self.files)}")
        for file in self.files:
            print(f"    \033[1;36m- {file['path']}\033[0m ({self.human_readable_size(file['length'])})")
        #print(f"\033[1;32m  Pieces (first 20 bytes):\033[0m \033[1;37m{self.pieces[:20]}\033[0m")
