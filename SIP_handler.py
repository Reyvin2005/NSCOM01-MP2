import socket
import threading
import time
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('SIP')

class SIPHandler:
    def __init__(self, local_ip, local_port, remote_ip, remote_port):
        self.local_ip = local_ip
        self.local_port = local_port
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.local_ip, self.local_port))
        self.call_id = f"{time.time()}@{local_ip}"
        self.tag = f"tag-{int(time.time())}"
        self.branch = f"z9hG4bK-{int(time.time())}"
        self.cseq = 1
        self.session_established = False
        self.rtp_port = None
        self.remote_rtp_port = None
        
    def create_invite(self, rtp_port):
        """Create SIP INVITE message with SDP"""
        self.rtp_port = rtp_port
        sdp = (
            f"v=0\r\n"
            f"o=user1 {int(time.time())} {int(time.time())} IN IP4 {self.local_ip}\r\n"
            f"s=SIP Call\r\n"
            f"c=IN IP4 {self.local_ip}\r\n"
            f"t=0 0\r\n"
            f"m=audio {rtp_port} RTP/AVP 0\r\n"  # G.711 u-law codec
            f"a=rtpmap:0 PCMU/8000\r\n"
        )
        
        invite = (
            f"INVITE sip:user@{self.remote_ip}:{self.remote_port} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {self.local_ip}:{self.local_port};branch={self.branch}\r\n"
            f"From: <sip:user@{self.local_ip}>;tag={self.tag}\r\n"
            f"To: <sip:user@{self.remote_ip}>\r\n"
            f"Call-ID: {self.call_id}\r\n"
            f"CSeq: {self.cseq} INVITE\r\n"
            f"Content-Type: application/sdp\r\n"
            f"Content-Length: {len(sdp)}\r\n"
            f"\r\n"
            f"{sdp}"
        )
        
        return invite.encode()
    
    def create_ok(self, rtp_port):
        """Create 200 OK message with SDP"""
        self.rtp_port = rtp_port
        sdp = (
            f"v=0\r\n"
            f"o=user2 {int(time.time())} {int(time.time())} IN IP4 {self.local_ip}\r\n"
            f"s=SIP Call\r\n"
            f"c=IN IP4 {self.local_ip}\r\n"
            f"t=0 0\r\n"
            f"m=audio {rtp_port} RTP/AVP 0\r\n"  # G.711 u-law codec
            f"a=rtpmap:0 PCMU/8000\r\n"
        )
        
        ok = (
            f"SIP/2.0 200 OK\r\n"
            f"Via: SIP/2.0/UDP {self.remote_ip}:{self.remote_port};branch={self.branch}\r\n"
            f"From: <sip:user@{self.remote_ip}>;tag={self.tag}\r\n"
            f"To: <sip:user@{self.local_ip}>;tag=responder-{int(time.time())}\r\n"
            f"Call-ID: {self.call_id}\r\n"
            f"CSeq: {self.cseq} INVITE\r\n"
            f"Content-Type: application/sdp\r\n"
            f"Content-Length: {len(sdp)}\r\n"
            f"\r\n"
            f"{sdp}"
        )
        
        return ok.encode()
    
    def create_ack(self):
        """Create ACK message"""
        ack = (
            f"ACK sip:user@{self.remote_ip}:{self.remote_port} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {self.local_ip}:{self.local_port};branch={self.branch}\r\n"
            f"From: <sip:user@{self.local_ip}>;tag={self.tag}\r\n"
            f"To: <sip:user@{self.remote_ip}>\r\n"
            f"Call-ID: {self.call_id}\r\n"
            f"CSeq: {self.cseq} ACK\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        
        return ack.encode()
    
    def create_bye(self):
        """Create BYE message"""
        self.cseq += 1
        bye = (
            f"BYE sip:user@{self.remote_ip}:{self.remote_port} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {self.local_ip}:{self.local_port};branch={self.branch}\r\n"
            f"From: <sip:user@{self.local_ip}>;tag={self.tag}\r\n"
            f"To: <sip:user@{self.remote_ip}>\r\n"
            f"Call-ID: {self.call_id}\r\n"
            f"CSeq: {self.cseq} BYE\r\n"
            f"Content-Length: 0\r\n"
            f"\r\n"
        )
        
        return bye.encode()
    
    def send_invite(self, rtp_port):
        """Send INVITE message to remote endpoint"""
        invite = self.create_invite(rtp_port)
        logger.info(f"Sending INVITE to {self.remote_ip}:{self.remote_port}")
        self.sock.sendto(invite, (self.remote_ip, self.remote_port))
    
    def send_ok(self, rtp_port):
        """Send 200 OK message to remote endpoint"""
        ok = self.create_ok(rtp_port)
        logger.info(f"Sending 200 OK to {self.remote_ip}:{self.remote_port}")
        self.sock.sendto(ok, (self.remote_ip, self.remote_port))
    
    def send_ack(self):
        """Send ACK message to remote endpoint"""
        ack = self.create_ack()
        logger.info(f"Sending ACK to {self.remote_ip}:{self.remote_port}")
        self.sock.sendto(ack, (self.remote_ip, self.remote_port))
    
    def send_bye(self):
        """Send BYE message to remote endpoint"""
        bye = self.create_bye()
        logger.info(f"Sending BYE to {self.remote_ip}:{self.remote_port}")
        self.sock.sendto(bye, (self.remote_ip, self.remote_port))
    
    def parse_sdp(self, message):
        """Extract RTP port from SDP body"""
        # Look for the audio line in SDP: m=audio PORT RTP/AVP...
        match = re.search(r'm=audio (\d+)', message)
        if match:
            return int(match.group(1))
        return None
    
    def handle_message(self, message):
        """Process incoming SIP messages"""
        message_str = message.decode('utf-8')
        logger.debug(f"Received SIP message:\n{message_str}")
        
        if message_str.startswith('INVITE'):
            logger.info("Received INVITE")
            self.remote_rtp_port = self.parse_sdp(message_str)
            logger.info(f"Extracted remote RTP port: {self.remote_rtp_port}")
            return 'INVITE'
            
        elif message_str.startswith('SIP/2.0 200'):
            logger.info("Received 200 OK")
            self.remote_rtp_port = self.parse_sdp(message_str)
            logger.info(f"Extracted remote RTP port: {self.remote_rtp_port}")
            return '200 OK'
            
        elif message_str.startswith('ACK'):
            logger.info("Received ACK")
            self.session_established = True
            return 'ACK'
            
        elif message_str.startswith('BYE'):
            logger.info("Received BYE")
            self.session_established = False
            # Send 200 OK response to BYE
            ok = (
                f"SIP/2.0 200 OK\r\n"
                f"Via: SIP/2.0/UDP {self.remote_ip}:{self.remote_port};branch={self.branch}\r\n"
                f"From: <sip:user@{self.remote_ip}>;tag={self.tag}\r\n"
                f"To: <sip:user@{self.local_ip}>;tag=responder-{int(time.time())}\r\n"
                f"Call-ID: {self.call_id}\r\n"
                f"CSeq: {self.cseq} BYE\r\n"
                f"Content-Length: 0\r\n"
                f"\r\n"
            )
            self.sock.sendto(ok.encode(), (self.remote_ip, self.remote_port))
            return 'BYE'
            
        elif message_str.startswith('SIP/2.0 4') or message_str.startswith('SIP/2.0 5'):
            logger.error(f"Received error response: {message_str.splitlines()[0]}")
            return 'ERROR'
            
        return None
    
    def listen(self, callback=None):
        """Start listening for incoming SIP messages"""
        def _listen():
            while True:
                try:
                    data, addr = self.sock.recvfrom(4096)
                    message_type = self.handle_message(data)
                    if callback and message_type:
                        callback(message_type)
                except Exception as e:
                    logger.error(f"Error in SIP listener: {e}")
        
        thread = threading.Thread(target=_listen, daemon=True)
        thread.start()
        return thread
    
    def close(self):
        """Close the socket"""
        self.sock.close()