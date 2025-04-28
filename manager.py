import asyncio
import random
import os
from   constant import *
from   printing import *
from   enum     import Enum
from   typing   import List
from   peer     import Peer
from   block    import Block, BlockStatus


class Manager:
    def __init__(self, peers: List[Peer], pieces: str, piece_size: int, info_hash: bytes, num_pieces: int, total_size: int):
        # Initialize the manager with pieces, peers, piece sizes, and total size
        self.pieces        = pieces
        self.peers         = []
        self.piece_size    = piece_size
        self.info_hash     = info_hash
        self.num_pieces    = num_pieces
        self.total_size    = total_size
        self.block_size    = pow(2, 14)   # Block size set to 16KB
        self.num_blocks    = self.piece_size // self.block_size
        
        # Create an async queue to hold blocks that need to be downloaded
        self.consume_queue = asyncio.Queue()
        self.request_queue = asyncio.Queue()

        # Generate a unique peer ID
        peer_id    = b'-PY0001-' + bytes(random.randint(0, 9) for _ in range(12))
        
        # Create the list of available peers
        self.peers = [Peer(peer_info=peer, info_hash=self.info_hash, peer_id=peer_id, 
                           consume_queue=self.consume_queue,
                           request_queue=self.request_queue) for peer in peers]

        # Generate the list of blocks representing pieces of the file
        self.blocks = self.__create_blocks()

    def __create_blocks(self):
        # Create blocks from the given pieces
        blocks = []
        for piece_index in range(self.num_pieces):
            # Compute the start and end of the current piece
            piece_start  = piece_index * self.piece_size
            piece_end    = min(piece_start + self.piece_size, self.total_size)
            piece_length = piece_end - piece_start
            
            # Divide each piece into smaller blocks
            offset = 0
            while offset < piece_length:
                block_length = min(self.block_size, piece_length - offset)
                block        = Block(piece_index=piece_index, block_offset=offset, length=block_length)
                blocks.append(block)
                offset += block_length

        return blocks

    async def consume_block(self):
        count = 0
        # Continue to consume data from peers
        while True:
            
            res, ip, port = await self.consume_queue.get()
            found     = False

            for i, block in enumerate(self.blocks):
                if block.piece_index == res.piece_index and block.block_offset == res.block_offset:
                    self.blocks[i].status = BlockStatus.DOWNLOADED
                    self.blocks[i].data = res.block_data
                    found  = True
                    count += 1
                    break
                    
            if found:
                print_blue(f"[MANAGER]: downloaded block, piece_index={res.piece_index}, block_offset={res.block_offset} from {ip} ({count}/{len(self.blocks)})")
                pass
                #pass
                #print_green(f"[MANAGER]: downloaded block, piece_index={res.piece_index}, block_offset={res.block_offset}")
                #print(f"[MANAGER]: download progress={count}/{len(self.blocks)}")
            
            self.consume_queue.task_done()
            await asyncio.sleep(delay=WAITING)

    async def request_block(self, batch_size: int = 20):
        while True:
            batch = []
            # Shuffle blocks to randomize the order of requesting
            random.shuffle(self.blocks)

            for block in self.blocks:
                if block.status == BlockStatus.NOT_REQUESTED:
                    batch.append(block)
                if len(batch) >= batch_size:
                    break

            # Put all blocks in the queue as a batch
            for block in batch:
                block: Block
                await self.request_queue.put(block)

            await asyncio.sleep(delay=WAITING)

    async def download(self):
        # Start the consumer to process block requests
        producer_task = asyncio.create_task(self.request_block())
        
        # Start the consumer to process block requests
        consumer_task = asyncio.create_task(self.consume_block())

        # Shuffle and create a list of tasks for connecting to the peers
        tasks = []
        random.shuffle(self.peers)

        # Connect to the first 10 peers (or as many as available)
        for peer in self.peers[:10]:
            peer: Peer
            task = asyncio.create_task(peer.download())
            tasks.append(task)

        # Wait for all peer connection tasks to complete
        await asyncio.gather(*tasks)

        # Wait for two last tasks
        await consumer_task
        await producer_task