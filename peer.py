import struct
import asyncio
from typing import Dict, Any, Optional

from constant  import *
from printing  import *
from protocol  import BitTorrentMessage
from block     import Block, BlockStatus


class Peer:
    def __init__(self, peer_info: Dict[str, Any], 
                       info_hash: bytes, 
                       peer_id: bytes, 
                       consume_queue: asyncio.Queue, 
                       request_queue: asyncio.Queue):
        
        self.ip            = peer_info["ip"]
        self.port          = peer_info["port"]
        self.info_hash     = info_hash
        self.peer_id       = peer_id
        self.choked        = True
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.consume_queue = consume_queue
        self.request_queue = request_queue
        self.connected     = False

    async def establish(self, timeout: int = 30) -> bool:
        """
        Open a TCP connection with the remote peer.
        If the connection is not established within `timeout` seconds,
        the connection attempt fails.
        """
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(host=self.ip, port=self.port), 
                timeout=timeout)
            
            print_green(f"[PEER={self.ip}]: Connection established")
            self.connected = True
            return True
        
        except Exception:
            self.connected = False
            #print_red(f"[PEER={self.ip}]: Connection refused")
            return False

    async def handshake(self) -> bool:
        """
        Handshake process according to BitTorrent specifications.
        """
        if not self.writer:
            #print_yellow(f"[PEER={self.ip}]: Handshake failed")
            return False

        # Send handshake message
        msg = BitTorrentMessage.create_handshake(info_hash=self.info_hash, peer_id=self.peer_id)
        self.writer.write(msg)
        await self.writer.drain()

        try:
            res = await self.reader.readexactly(68)
            res = BitTorrentMessage.parse_handshake(data=res)

            if res is None:
                #print_yellow(f"[PEER={self.ip}]: Handshake failed")
                return False

            # Send interested message
            interested_msg = BitTorrentMessage.create_interested()
            self.writer.write(interested_msg)
            await self.writer.drain()

            #print_green(f"[PEER={self.ip}]: Interested sent")
            print_green(f"[PEER={self.ip}]: Handshake successful")
            return True
        
        except (asyncio.IncompleteReadError, Exception):
            #print_yellow(f"[PEER={self.ip}]: Handshake failed")
            return False

    async def process_requests(self):
        """
        Consume the request queue, send requests to the peer.
        """
        while True:
            try:
                block = await self.request_queue.get()

                if not self.writer:
                    print_red(f"[PEER={self.ip}]: Cannot access socket")
                    return

                # If a request for a block has been received, generate the BitTorrent
                # message for requesting the block
                if block:
                    block: Block
                    msg = BitTorrentMessage.create_request(index=block.piece_index, 
                                                           begin=block.block_offset,
                                                           length=block.block_length)
                    self.writer.write(msg)
                    await self.writer.drain()

                self.request_queue.task_done()
                await asyncio.sleep(WAITING)

            except (asyncio.CancelledError, ConnectionResetError):
                #print_red(f"[PEER={self.ip}]: Socket closed")
                return
            except Exception:
                #print_red(f"[PEER={self.ip}]: Error while requesting data")
                return

    async def process_replies(self):
        """
        Receive replies from the peer and put completed blocks into consume_queue.
        """
        try:
            while True:
                len_prefix   = await self.reader.readexactly(4)
                (len_value,) = struct.unpack(">I", len_prefix)

                if len_value == 0:
                    continue  # Keep-alive message

                data = await self.reader.readexactly(len_value)
                if len(data) > 0:
                    message_id = data[0]

                    if message_id == BitTorrentMessage.CHOKE:
                        self.choked = True

                    elif message_id == BitTorrentMessage.UNCHOKE:
                        self.choked = False

                    elif message_id == BitTorrentMessage.PIECE:
                        # Extract the location of the block in the torrent file
                        piece_index, block_offset = struct.unpack(">II", data[1:9])
                        block_data = data[9:]

                        # Generate the block that has been downloaded
                        block = Block(piece_index=piece_index, block_offset=block_offset, length=len(block_data),
                                      block_data=block_data, status=BlockStatus.DOWNLOADED)

                        await self.consume_queue.put((block, self.ip, self.port))
                        await asyncio.sleep(WAITING)

        except (asyncio.CancelledError, asyncio.IncompleteReadError, ConnectionResetError):
            return
        except Exception:
            return

    async def download(self):
        
        """
        Handles the download logic: establish connection, perform handshake, 
        and process requests and replies.
        """
        
        timeout = 20

        while True:
            if await self.establish() and await self.handshake():
                requests_task = asyncio.create_task(self.process_requests())
                replies_task  = asyncio.create_task(self.process_replies())

                await asyncio.gather(replies_task, requests_task)
            else:
                #print_yellow(f"[PEER={self.ip}]: Retrying connection in {timeout} seconds")
                await asyncio.sleep(timeout)
