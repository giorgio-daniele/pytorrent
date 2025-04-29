import struct
import asyncio
from   typing import Dict, Any, Optional

from constant  import *
from printing  import *
from protocol  import Message
from block     import Block, BlockStatus


class Peer:
    def __init__(self, peer_info: Dict[str, Any], 
                       info_hash: bytes, 
                       peer_id: bytes, 
                       consume_queue: asyncio.Queue, 
                       request_queue: asyncio.Queue,
                       complete:      asyncio.Event,
                       availability:  list[int]):
        
        self.ip            = peer_info["ip"]
        self.port          = peer_info["port"]
        self.info_hash     = info_hash
        self.peer_id       = peer_id
        self.choked        = True
        
        self.consume_queue = consume_queue
        self.request_queue = request_queue
        self.connected     = False
        
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.complete = complete
        
        self.availability = availability
        
    async def __read_timeout(self, n: int, timeout: int = 5):
        try:
            return await asyncio.wait_for(self.reader.readexactly(n), timeout=timeout)
        except asyncio.TimeoutError:
            raise Exception(f"Read operation timed out after {timeout} seconds")
        except Exception as err:
            raise Exception(f"Error while reading: {err}")

    async def __write_timeout(self, msg: bytes, timeout: int = 5):
        try:
            self.writer.write(msg)
            await asyncio.wait_for(self.writer.drain(), timeout=timeout)
        except asyncio.TimeoutError:
            raise Exception(f"Write operation timed out after {timeout} seconds")
        except Exception as err:
            raise Exception(f"Error while writing: {err}")

    """
    
    Before starting sharing data, the client has to establish a TCP connection.
    Once the TCP connection is established, the client has to handshake the peer.
    The handshake process requires the client to send and receive a specific
    sequence of BitTorrent bytes
    
    """


    async def __establish(self, timeout: int = 30) -> bool:
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(host=self.ip, port=self.port), timeout=timeout)
            
            print_green(f"[PEER={self.ip}]: Connection established")
            self.connected = True
            return True
        except asyncio.TimeoutError:
            #print_yellow(f"[PEER={self.ip}]: Connection attempt timed out")
            self.connected = False
            return False
        except Exception as err:
            #print_red(f"[PEER={self.ip}]: Connection failed - {err}")
            self.connected = False
            return False

    async def __handshake(self) -> bool:
        if not self.writer:
            return False

        try:
            # Send handshake
            msg = Message.create_handshake(info_hash=self.info_hash, peer_id=self.peer_id)
            self.writer.write(msg)
            await self.writer.drain()

            # Receive handshake response
            res = await self.__read_timeout(n=68)
            msg = Message.parse_handshake(data=res)

            if msg is None:
                return False

            # Send interested message
            interested_msg = Message.create_interested()
            await self.__write_timeout(msg=interested_msg)

            #print_green(f"[PEER={self.ip}]: Handshake and Interested message sent")
            return True
        
        except (asyncio.IncompleteReadError, Exception) as err:
            #print_yellow(f"[PEER={self.ip}]: Handshake failed: {err}")
            return False

    """
    
    The client runs two seperate tasks: __request_data() and __consume_data(). The
    first is used to extract requests fro queue filled in manager.py, while the
    second is used to transfer downloaded data to manager.py
    
    """

    async def __request_data(self):
        while not self.complete.is_set():
            try:
                block: Block = await self.request_queue.get()

                if self.writer is None:
                    return

                if block:
                    msg = Message.create_request(index=block.index, begin=block.offset, length=block.length)
                    self.writer.write(msg)
                    await self.writer.drain()

                self.request_queue.task_done()
                await asyncio.sleep(WAITING)
            except Exception as err:
                #print_yellow(f"[PEER={self.ip}]: Error while requesting data: {err}")
                return

    async def __consume_data(self):
        while not self.complete.is_set():
            try:
                len_prefix = await self.reader.readexactly(4)
                (len_value,) = struct.unpack(">I", len_prefix)

                if len_value == 0:
                    continue  # Keep-alive

                data = await self.reader.readexactly(len_value)

                if data:
                    msg_id = data[0]

                    if msg_id == Message.CHOKE:
                        self.choked = True

                    elif msg_id == Message.UNCHOKE:
                        self.choked = False
                        
                    elif msg_id == Message.HAVE:
                        index = struct.unpack(">I", data[1:5])[0]
                        if 0 <= index < len(self.availability):
                            self.availability[index] += 1

                    elif msg_id == Message.BITFIELD:
                        bitfield = data[1:]
                        for i in range(len(bitfield) * 8):
                            byte_index = i // 8
                            bit_index  = 7 - (i % 8)
                            if byte_index < len(bitfield) and (bitfield[byte_index] >> bit_index) & 1:
                                self.availability[i] += 1

                    elif msg_id == Message.PIECE:
                        index, offset = struct.unpack(">II", data[1:9])
                        payload = data[9:]

                        block = Block(index=index, offset=offset, length=len(payload), data=payload, status=BlockStatus.DOWNLOADED)
                        await self.consume_queue.put((block, self.ip, self.port))
                        await asyncio.sleep(WAITING)

            except Exception as err:
                #print_yellow(f"[PEER={self.ip}]: Error while consuming data: {err}")
                return

    """
    
    The method download is used to trigger the runtime of each peer
    
    """

    async def download(self):
        
        timeout = 25  # seconds

        while not self.complete.is_set():
            if await self.__establish() and await self.__handshake():
                try:
                    request_task = asyncio.create_task(self.__request_data())
                    consume_task = asyncio.create_task(self.__consume_data())

                    await asyncio.gather(request_task, consume_task)
                except Exception as err:
                    #print_red(f"[PEER={self.ip}]: Unexpected error in download loop: {err}")
                    return
            else:
                #print_yellow(f"[PEER={self.ip}]: Retrying connection after {timeout} seconds...")
                await asyncio.sleep(timeout)
