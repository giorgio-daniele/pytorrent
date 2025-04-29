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
        self.block_size     = min(pow(2, 16), self.piece_size)
        self.peers          = peers
        
        self.consume_queue  = asyncio.Queue()
        self.request_queue  = asyncio.Queue()
        self.complete       = asyncio.Event()

        # Create a random peer_id
        peer_id = b'-PY0001-' + bytes(random.randint(0, 9) for _ in range(12))
    
        # Generate the list of blocks
        self.blocks = self.__create_blocks()
        
        # Track pieces availability
        self.availability = [0] * self.num_pieces
        
        # Create the list of all peers
        self.peers = [Peer(peer_info=peer, info_hash=self.info_hash, peer_id=peer_id,
                           consume_queue=self.consume_queue,
                           request_queue=self.request_queue, complete=self.complete,
                           availability=self.availability) for peer in peers]

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
        count = 0
        total_blocks = len(self.blocks)
        
        downloaded_size = 0
        total_size      = sum(block.length for block in self.blocks)
        batch_size      = 20

        while not self.complete.is_set():
            batch = []
            try:
                res = await self.consume_queue.get()
                batch.append(res)
                self.consume_queue.task_done()

                # Now collect up to BATCH_SIZE - 1 more without waiting
                for _ in range(batch_size - 1):
                    try:
                        res = self.consume_queue.get_nowait()
                        batch.append(res)
                        self.consume_queue.task_done()
                    except asyncio.QueueEmpty:
                        break

            except Exception as err:
                continue
            
            # Process the batch of blocks dequeued
            for res, ip, port in batch:
                res: Block

                for block in self.blocks:
                    block: Block
                    if block.index == res.index and block.offset == res.offset:
                        if block.status != BlockStatus.DOWNLOADED:
                            block.status = BlockStatus.DOWNLOADED
                            block.data       = res.data
                            count           += 1
                            downloaded_size += block.length
                        break
            
            # Calculate and print progress after the batch
            progress = (downloaded_size / total_size) * 100
            print_blue(f"[info]: downloading... {downloaded_size} out of {total_size} bytes, {progress:.2f}%)")

            await asyncio.sleep(WAITING)

            if count >= total_blocks:
                self.complete.set()
                print_green("[MANAGER]: All blocks downloaded successfully!")

    async def __request_data(self, batch_size: int = 20):
        while not self.complete.is_set():
            
            batch = [
                block for block in random.sample(self.blocks, len(self.blocks))
                if block.status == BlockStatus.NOT_REQUESTED
            ][:batch_size]
            
            # # Get the list of all not downloaded blocks
            # not_requested_blocks = [
            #     block for block in self.blocks
            #     if block.status == BlockStatus.NOT_REQUESTED
            # ]

            # # Sort blocks according to those that are rare
            # not_requested_blocks.sort(key=lambda b: self.availability[b.index])

            # # Generate the batch to be downloaded
            # batch = not_requested_blocks[:batch_size]

            for block in batch:
                block: Block
                await self.request_queue.put(block)
            await asyncio.sleep(WAITING)
    
    """
    
    The method download is used to trigger the runtime of each peer
    
    """

        
    async def download(self):
        producer_task = asyncio.create_task(self.__request_data())
        consumer_task = asyncio.create_task(self.__consume_data())

        for peer in random.sample(self.peers, min(40, len(self.peers))):
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
