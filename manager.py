import asyncio
import random
from   typing import List

from constant import *
from printing import *
from peer     import Peer
from block    import Block, BlockStatus
from torrent  import Torrent


class Manager:
    def __init__(self, torrent: Torrent, peers: List[Peer]):
        self.files          = torrent.files
        self.pieces         = torrent.pieces
        self.piece_size     = torrent.piece_length
        self.info_hash      = torrent.info_hash
        self.num_pieces     = torrent.num_pieces
        self.total_size     = torrent.total_size
        self.block_size     = min(pow(2, 14), self.piece_size)
        self.peers          = peers
        
        self.consume_queue  = asyncio.Queue()
        self.request_queue  = asyncio.Queue()
        self.complete       = asyncio.Event()

        # Create a random peer_id
        peer_id = b'-PY0001-' + bytes(random.randint(0, 9) for _ in range(12))
        
        # Create the list of all peers
        self.peers = [Peer(peer_info=peer, info_hash=self.info_hash, peer_id=peer_id,
                           consume_queue=self.consume_queue,
                           request_queue=self.request_queue, complete=self.complete) for peer in peers]

        # Generate the list of blocks
        self.blocks = self.__create_blocks()

    def __create_blocks(self) -> List[Block]:
        blocks = []

        for piece_index in range(self.num_pieces):
            piece_start = piece_index * self.piece_size
            piece_end   = min(piece_start + self.piece_size, self.total_size)
            offset      = 0

            while offset < (piece_end - piece_start):
                block_length = min(self.block_size, piece_end - piece_start - offset)
                blocks.append(Block(index=piece_index, offset=offset, length=block_length))
                offset += block_length

        return blocks


    """
    
    The client runs two seperate tasks: __request_data() and __consume_data(). The
    first is used to request data to peers, while the second is used to collect data
    to be assembled later on
    
    """

    async def __consume_data(self):
        count        = 0
        total_blocks = len(self.blocks)

        while not self.complete.is_set():
            res, ip, port = await self.consume_queue.get()
            res: Block

            for block in self.blocks:
                block: Block
                if block.index == res.index and block.offset == res.offset:
                    if block.status != BlockStatus.DOWNLOADED:
                        block.status = BlockStatus.DOWNLOADED
                        block.data   = res.data
                        count       += 1
                        
                        # Calculate progress and print it
                        progress = (count / total_blocks) * 100
                        print_blue(f"[info]: downloading... from {ip}, {count}/{total_blocks} blocks ({progress:.2f}%)")
                    break

            self.consume_queue.task_done()
            await asyncio.sleep(WAITING)
            
            if count >= total_blocks:
                self.complete.set()
                print_green("[MANAGER]: All blocks downloaded successfully!")

    async def __request_data(self, batch_size: int = 12):
        while not self.complete.is_set():
            batch = [
                block for block in random.sample(self.blocks, len(self.blocks))
                if block.status == BlockStatus.NOT_REQUESTED
            ][:batch_size]

            for block in batch:
                block: Block
                await self.request_queue.put(block)
            await asyncio.sleep(WAITING)

        print_yellow("[MANAGER]: Stopped requesting blocks.")
    
    """
    
    The method download is used to trigger the runtime of each peer
    
    """

        
    async def download(self):
        producer_task = asyncio.create_task(self.__request_data())
        consumer_task = asyncio.create_task(self.__consume_data())

        for peer in random.sample(self.peers, min(30, len(self.peers))):
            asyncio.create_task(peer.download())

        await self.complete.wait()

        producer_task.cancel()
        consumer_task.cancel()

        try:
            await producer_task
        except asyncio.CancelledError:
            pass

        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
        
        print_green("[MANAGER]: All downloads finished. Saving file...")
        self.save(self.files[0]["path"])

    def save(self, filename: str):
        print_blue(f"[MANAGER]: Saving data to {filename}...")

        if any(block.status != BlockStatus.DOWNLOADED for block in self.blocks):
            raise Exception("[MANAGER]: Cannot save, some blocks are missing!")

        sorted_blocks = sorted(self.blocks, key=lambda b: (b.index, b.offset))
        full_data     = b''.join(block.data for block in sorted_blocks)

        with open(filename, 'wb') as f:
            f.write(full_data)

        print_green(f"[MANAGER]: Saved successfully to {filename}. Size: {len(full_data)} bytes.")
