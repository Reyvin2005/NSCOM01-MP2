class SipPacket:
    """
    SIP packet implementation for VoIP signaling.
    
    Handles creation and encoding of SIP messages for:
    - Call setup (INVITE)
    - Call responses (200 OK)
    - Call teardown (BYE)
    - Session acknowledgment (ACK)
    """
    
    def __init__(self):
        """Initialize SIP packet with empty fields."""
        self.method = ""
        self.status_code = 0
        self.call_id = ""
        self.cseq = 0
        self.from_addr = ""
        self.to_addr = ""
        self.content_type = ""
        self.content = ""
        self.reason = ""  # Required for response messages
    
    def create_invite(self, from_addr, to_addr, call_id, cseq, sdp_content):
        """Create SIP INVITE message"""
        self.method = "INVITE"
        self.call_id = call_id
        self.cseq = cseq
        self.from_addr = from_addr
        self.to_addr = to_addr
        self.content_type = "application/sdp"
        self.content = sdp_content
        
    def create_response(self, status_code, reason="OK"):
        """Create SIP response"""
        self.status_code = status_code
        self.reason = reason
        
    def encode(self):
        """Convert SIP message to bytes"""
        if self.method:
            # Request
            msg = f"{self.method} sip:{self.to_addr} SIP/2.0\r\n"
        else:
            # Response
            msg = f"SIP/2.0 {self.status_code} OK\r\n"
            
        msg += f"Via: SIP/2.0/UDP {self.from_addr}\r\n"
        msg += f"From: <sip:{self.from_addr}>\r\n"
        msg += f"To: <sip:{self.to_addr}>\r\n"
        msg += f"Call-ID: {self.call_id}\r\n"
        msg += f"CSeq: {self.cseq} {self.method}\r\n"
        
        if self.content:
            msg += f"Content-Type: {self.content_type}\r\n"
            msg += f"Content-Length: {len(self.content)}\r\n\r\n"
            msg += self.content
        else:
            msg += "Content-Length: 0\r\n\r\n"
            
        return msg.encode()