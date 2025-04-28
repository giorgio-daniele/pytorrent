#!/usr/bin/env python3

import asyncio
import random
from   torrent import Torrent
from   tracker import Tracker
from   manager import Manager
# from   peer_connection import PeerConnection

async def main():

    # Load a torrent file
    file_name = 'debian.torrent'
    torrent   = Torrent.from_file(file_name)
    
    # Debug the torrent
    torrent.debug_print()
    
    print("=================")
    
    # Generate a random peer ID (conventionally -XX0000-<random digits>)
    peer_id = b'-PY0001-' + bytes(random.randint(0, 9) for _ in range(12))
    
    # Create a tracker object
    tracker = Tracker(torrent, peer_id)
    
    # Announce to the tracker
    peers = await tracker.announce(port=6881)
    
    
    # Create a new manager
    manager = Manager(pieces=torrent.pieces, peers=peers, piece_size=torrent.piece_length, info_hash=torrent._calculate_info_hash(), 
                      num_pieces=torrent.num_pieces, 
                      total_size=torrent.size)
    
    await manager.download()
    
    # # Try to connect to each peer
    # connection_tasks = []
    # for peer in peers[:5]:  # Limit to first 5 peers
    #     connection = Peer(peer, torrent.info_hash, peer_id)
    #     connection_tasks.append(connection.connect())
    
    # # Wait for all connection attempts
    # await asyncio.gather(*connection_tasks)

if __name__ == "__main__":
    asyncio.run(main())