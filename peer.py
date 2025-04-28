import struct
import asyncio
from   constant  import *
from   printing  import *
from   typing    import Dict, Any, Optional
from   protocol  import BitTorrentMessage
from   block     import Block, BlockStatus

class Peer:
    def __init__(self, peer_info: Dict[str, Any], 
                       info_hash: bytes, 
                       peer_id:   bytes, 
                       consume_queue: asyncio.Queue, 
                       request_queue: asyncio.Queue):
        
        self.ip   = peer_info["ip"]
        self.port = peer_info["port"]
        self.info_hash = info_hash
        self.peer_id   = peer_id
        self.choked    = True
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.consume_queue = consume_queue
        self.request_queue = request_queue
        self.connected     = False

    async def establish(self, timeout: int = 30) -> bool:
        
        """
        Open a TCP connection with the remote peer. If the
        connection is not established within tiemeout secs,
        the connection attempt fails
        """
    
        try:
            self.reader, self.writer = await asyncio.wait_for(asyncio.open_connection(host=self.ip, port=self.port), timeout=timeout)
            
            print_green(f"[PEER={self.ip}]: connection established")
            self.connected = True
            return True
        
        except Exception as err:
            self.connected = False
            print_red(f"[PEER={self.ip}]: connection refused")
            return False

    async def handshake(self) -> bool:
        
        """
        Within a TCP connection, the client handshakes the peer. The
        handshake process is driven by BitTorrent specifications
        """
    
        if not self.writer:
            print_yellow(f"[PEER={self.ip}]: handshake failed")
            return False
        
        # Send the message
        msg = BitTorrentMessage.create_handshake(info_hash=self.info_hash, peer_id=self.peer_id)
        self.writer.write(msg)
        await self.writer.drain()
        
        # Read the message
        try:
            res = await self.reader.readexactly(68)
            res = BitTorrentMessage.parse_handshake(data=res)
            
            if res is None:
                print_yellow(f"[PEER={self.ip}]: handshake failed")
                return False
            else:
                # Send interested message after successful handshake
                interested_msg = BitTorrentMessage.create_interested()
                self.writer.write(interested_msg)
                await self.writer.drain()
                print_green(f"[PEER={self.ip}]: interested sent ")
                
            print_green(f"[PEER={self.ip}]: handshake okay")
            return True
       
        except asyncio.IncompleteReadError:
            print_yellow(f"[PEER={self.ip}]: handshake failed")
            return False
        except Exception as e:
            print_yellow(f"[PEER={self.ip}]: handshake failed")
            return False
        

    async def process_requests(self):
        
        """
        Considering request_queue, the client extract a block to be
        requested and send it using the BitTorrent specifications
        """
        
        while True:
            try:
                block = await self.request_queue.get()
                
                if not self.writer:
                    print_red(f"[PEER={self.ip}]: can't access anymore the socket")
                    return
                
                if block:
                #if not self.choked and block:
                    block: Block
                    msg = BitTorrentMessage.create_request(index=block.piece_index, 
                                                           begin=block.block_offset, length=block.block_length)
                    
                    #print_blue(f"[PEER={self.ip}]: requesting {block}")
                    self.writer.write(msg)
                    await self.writer.drain()
                    
                self.request_queue.task_done()
                await asyncio.sleep(delay=WAITING)
            
            except (asyncio.CancelledError, ConnectionResetError) as e:
                print_red(f"[PEER={self.ip}]: can't access anymore the socket")
                # await self.reconnect()
                return
            except Exception as e:
                print_red(f"[PEER={self.ip}]: error while requesting data")
                # await self.reconnect()
                return

    async def process_replies(self):

        """
        Considering consume_queue, push the block that have been
        downlaoded from the peer by the client
        """
        
        try:
            while True:
                len_prefix   = await self.reader.readexactly(4)
                (len_value,) = struct.unpack(">I", len_prefix)
                
                # This is a keep-alive message
                if len_value == 0:
                    continue
                
                data = await self.reader.readexactly(len_value)
                if len(data) > 0:
                    id = data[0]
                
                    if id == BitTorrentMessage.CHOKE:
                        self.choked = True
                        #print(f"[DEBUG] Choked by {self.peer_info['ip']}")
                        
                    elif id == BitTorrentMessage.UNCHOKE:
                        self.choked = False
                        #print(f"[DEBUG] Unchoked by {self.peer_info['ip']}")
                        
                    elif id == BitTorrentMessage.PIECE:
                        #print("PIECE")
                        piece_index, block_offset = struct.unpack(">II", data[1:9])
                        block_data = data[9:]
                        
                        # Create the block object
                        block = Block(piece_index=piece_index, block_offset=block_offset, length=len(block_data), 
                                      block_data=block_data, status=BlockStatus.DOWNLOADED)
                        
                        #print("CIAO")
                        
                        # Write the downloaded block in the queue
                        await self.consume_queue.put((block, self.ip, self.port))
                        await asyncio.sleep(delay=WAITING)
                        
        except (asyncio.CancelledError, asyncio.IncompleteReadError, ConnectionResetError) as e:
            #print(f"[ERROR] Connection reset or lost while processing replies: {e}")
            #await self.reconnect()
            return
        except Exception as e:
            #print(f"[ERROR] Error in process_replies: {e}")
            #await self.reconnect()
            return

    async def download(self):
        timeout  = 20
        
        """
        If the connection with the remote peer fails or the handshake fails,
        the client can establish and handshake again after a timeout 
        """
        
        while True:
            if await self.establish() and await self.handshake():
                requests_task = asyncio.create_task(self.process_requests())
                replies_task  = asyncio.create_task(self.process_replies())
                await asyncio.gather(replies_task, requests_task)
            else:
                print_yellow(f"[PEER={self.ip}]: retring connect after {timeout} seconds")
                await asyncio.sleep(delay=timeout)