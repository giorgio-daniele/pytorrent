# PyTorrent

**PyTorrent** is a lightweight BitTorrent client built with Python and `asyncio`.  
It connects to peers, downloads files block-by-block, verifies piece hashes, and saves the final file locally.

## Features
- Asynchronous peer-to-peer downloading
- SHA1 piece verification for data integrity
- Support for multiple peers and concurrent requests
- Simple and minimalistic design

## Requirements
- Python 3.9+
- Install dependencies:
  ```bash
  pip install -r requirements.txt

## Planned Features
- Supporting multi-file torrents
- Supporting trackers over UDP