from time import time

class RtpPacket:
    """
    RTP packet implementation for audio streaming.
    
    Attributes:
        HEADER_SIZE (int): Fixed size of RTP header (12 bytes)
        header (bytearray): RTP header containing protocol information
        payload (bytes): Audio data payload
    """

    HEADER_SIZE = 12
    
    def __init__(self):
        self.header = bytearray(self.HEADER_SIZE)
        self.payload = None
        
    def encode(self, version, padding, extension, cc, seqnum, marker, pt, ssrc, payload):
        """Encode the RTP packet with header fields and payload."""
        timestamp = int(time())
        
        # Fill the header bytearray with RTP header fields
        self.header[0] = (version << 6) | (padding << 5) | (extension << 4) | cc
        self.header[1] = (marker << 7) | pt
        self.header[2] = (seqnum >> 8) & 0xFF
        self.header[3] = seqnum & 0xFF
        self.header[4] = (timestamp >> 24) & 0xFF
        self.header[5] = (timestamp >> 16) & 0xFF
        self.header[6] = (timestamp >> 8) & 0xFF
        self.header[7] = timestamp & 0xFF
        self.header[8] = (ssrc >> 24) & 0xFF
        self.header[9] = (ssrc >> 16) & 0xFF
        self.header[10] = (ssrc >> 8) & 0xFF
        self.header[11] = ssrc & 0xFF
        
        # Store the payload
        self.payload = payload

    def decode(self, byteStream):
        """Decode the RTP packet."""
        self.header = bytearray(byteStream[:self.HEADER_SIZE])
        self.payload = byteStream[self.HEADER_SIZE:]
    
    def seqNum(self):
        """Return sequence (frame) number."""
        seqNum = self.header[2] << 8 | self.header[3]
        return int(seqNum)
    
    def getPayload(self):
        """Return payload."""
        return self.payload
        
    def getPacket(self):
        """Return RTP packet."""
        if self.payload is None:
            return self.header
        return bytes(self.header) + self.payload