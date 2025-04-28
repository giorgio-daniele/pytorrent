#!/usr/bin/env python3

import asyncio
import argparse
import random
import sys
from torrent import Torrent
from tracker import Tracker
from manager import Manager
from printing import *


async def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Torrent Downloader")
    parser.add_argument("t", help="Path to the torrent file", type=str)

    # Parse the command line arguments
    args = parser.parse_args()

    # Load the torrent file
    file_name = args.t
    try:
        torrent = Torrent.from_file(file_name)
    except Exception as e:
        print_red(f"[MAIN]: Can't parse the torrent file")
        print_yellow(f"[MAIN]: Exiting the program...")
        sys.exit(-1)
    
    if len(torrent.files) > 1:
        print_red(f"[error]: Multi-file torrents are not currently supported")
        print_yellow(f"[MAIN]: Exiting the program...")
        sys.exit(-3)
    
    # Debug the torrent (optional)
    torrent.debug_print()
    
    # Generate a random peer ID (conventionally -XX0000-<random digits>)
    peer_id = b'-PY0001-' + bytes(random.randint(0, 9) for _ in range(12))
    
    # Create a tracker object
    tracker = Tracker(torrent, peer_id)
    
    # Announce to the tracker and get the peers
    peers = await tracker.announce(port=6881)
    
    # Create a new manager
    manager = Manager(torrent=torrent, peers=peers)
    
    # Start the download
    await manager.download()

if __name__ == "__main__":
    asyncio.run(main())
