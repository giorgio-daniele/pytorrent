import struct
import urllib.parse
import aiohttp
import bencodepy
from   typing import List, Dict, Any
from   torrent import Torrent

class Tracker:

    def __init__(self, torrent: Torrent, peer_id: bytes):
        self.torrent   = torrent
        self.peer_id   = peer_id
        self.info_hash = torrent.info_hash
    
    async def announce(self, port: int = 6881, uploaded: int = 0, downloaded: int = 0, left: int = None) -> List[Dict[str, Any]]:
        
        if left is None:
            left = self.torrent.size - downloaded
        
        # Prepare tracker request params - non-binary params first
        params = {
            'port'        : port,
            'uploaded'    : uploaded,
            'downloaded'  : downloaded,
            'left'        : left,
            'compact'     : 1,
            'event'       : 'started'
        }
        
        # Convert params to query string
        query_string = urllib.parse.urlencode(params)
        
        # Add binary params
        # info_hash and peer_id need to be URL-encoded properly
        query_string += f"&info_hash={urllib.parse.quote_plus(self.info_hash)}"
        query_string += f"&peer_id={urllib.parse.quote_plus(self.peer_id)}"
        
        # Get announce URL from the torrent file
        announce_url = self.torrent.announce_url
        full_url     = f"{announce_url}?{query_string}"
        
        try:
            # Use aiohttp for the tracker request
            async with aiohttp.ClientSession() as s:
                async with s.get(full_url) as res:
                    if res.status != 200:
                        return []
                    
                    # Read and parse the tracker response
                    response_data = await res.read()
                    return self._parse_tracker_response(response_data)
                    
        except aiohttp.ClientError as e:
            print(f"Error connecting to tracker: {e}")
            return []
    
    def _parse_tracker_response(self, response_data: bytes) -> List[Dict[str, Any]]:
        try:
            # Parse tracker response (bencoded)
            res = bencodepy.decode(response_data)
            
            if b'failure reason' in res:
                failure = res[b'failure reason'].decode('utf-8')
                print(f"Tracker error: {failure}")
                return []
            
            # Extract peers info
            peers = []
            if b'peers' in res:
                peer_data = res[b'peers']
                
                if isinstance(peer_data, list):
                    # Dictionary model peers
                    for peer in peer_data:
                        peers.append({
                            'ip'    : peer[b'ip'].decode('utf-8'),
                            'port'  : peer[b'port']
                        })
                elif isinstance(peer_data, bytes):
                    # Compact model peers: 6 bytes per peer (4 for IP, 2 for port)
                    for i in range(0, len(peer_data), 6):
                        ip    = '.'.join(str(b) for b in peer_data[i:i+4])
                        port  = struct.unpack('>H', peer_data[i+4:i+6])[0]
                        peers.append({'ip': ip, 'port': port})
            
            # Print some tracker response stats
            # if b'interval' in res:
            #     print(f"Tracker suggests announcement interval: {res[b'interval']} seconds")
            # if b'complete' in res:
            #     print(f"Seeders: {res[b'complete']}")
            # if b'incomplete' in res:
            #     print(f"Leechers: {res[b'incomplete']}")
                        
            return peers
            
        except Exception as e:
            print(f"Error parsing tracker response: {e}")
            return []