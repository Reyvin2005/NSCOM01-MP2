import argparse
import logging
import time
import sys
from sip_handler import SIPHandler
from rtp_handler import RTPHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Client')

class VoIPClient:
    def __init__(self, local_ip, local_sip_port, local_rtp_port):
        self.local_ip = local_ip
        self.local_sip_port = local_sip_port
        self.local_rtp_port = local_rtp_port
        self.remote_ip = None
        self.remote_sip_port = None
        self.remote_rtp_port = None
        
        self.sip_handler = None
        self.rtp_handler = None
        self.call_in_progress = False
        
    def setup_handlers(self, remote_ip, remote_sip_port, remote_rtp_port=None):
        """Setup SIP and RTP handlers"""
        self.remote_ip = remote_ip
        self.remote_sip_port = remote_sip_port
        self.remote_rtp_port = remote_rtp_port if remote_rtp_port else None
        
        # Initialize SIP handler
        self.sip_handler = SIPHandler(
            self.local_ip, 
            self.local_sip_port, 
            self.remote_ip, 
            self.remote_sip_port
        )
        
        # Start SIP listener
        self.sip_handler.listen(callback=self.handle_sip_event)
        
        # Initialize RTP handler
        if self.remote_rtp_port:
            self._setup_rtp_handler(self.remote_rtp_port)
        
    def _setup_rtp_handler(self, remote_rtp_port):
        """Setup RTP handler with given remote port"""
        self.rtp_handler = RTPHandler(
            self.local_ip,
            self.local_rtp_port,
            self.remote_ip,
            remote_rtp_port
        )
    
    def initiate_call(self):
        """Initiate a call by sending SIP INVITE"""
        if not self.sip_handler:
            logger.error("SIP handler not initialized")
            return False
        
        logger.info(f"Initiating call to {self.remote_ip}:{self.remote_sip_port}")
        # Send INVITE with our RTP port
        self.sip_handler.send_invite(self.local_rtp_port)
        return True
    
    def end_call(self):
        """End the call by sending SIP BYE"""
        if not self.sip_handler or not self.call_in_progress:
            logger.warning("No call in progress to end")
            return False
        
        logger.info("Ending call")
        self.sip_handler.send_bye()
        self.call_in_progress = False
        
        if self.rtp_handler:
            self.rtp_handler.stop()
        
        return True
    
    def stream_audio(self, audio_file_path):
        """Stream audio file to remote endpoint"""
        if not self.rtp_handler or not self.call_in_progress:
            logger.error("Call not established or RTP handler not initialized")
            return False
        
        logger.info(f"Starting to stream audio file: {audio_file_path}")
        self.rtp_handler.start_streaming(audio_file_path)
        return True
    
    def handle_sip_event(self, event_type):
        """Handle SIP events"""
        logger.info(f"Handling SIP event: {event_type}")
        
        if event_type == 'INVITE':
            # We received an INVITE, setup RTP and respond with 200 OK
            remote_rtp_port = self.sip_handler.remote_rtp_port
            logger.info(f"Received call from {self.remote_ip}, remote RTP port: {remote_rtp_port}")
            
            if not self.rtp_handler and remote_rtp_port:
                self._setup_rtp_handler(remote_rtp_port)
            
            # Start RTP receiver to listen for incoming audio
            if self.rtp_handler:
                self.rtp_handler.start_receiving()
            
            # Send 200 OK with our RTP port
            self.sip_handler.send_ok(self.local_rtp_port)
            
        elif event_type == '200 OK':
            # Our INVITE was accepted, setup RTP with remote port from SDP
            remote_rtp_port = self.sip_handler.remote_rtp_port
            logger.info(f"Call accepted, remote RTP port: {remote_rtp_port}")
            
            if not self.rtp_handler and remote_rtp_port:
                self._setup_rtp_handler(remote_rtp_port)
            
            # Send ACK
            self.sip_handler.send_ack()
            self.call_in_progress = True
            
        elif event_type == 'ACK':
            # Call setup completed
            logger.info("Call established")
            self.call_in_progress = True
            
        elif event_type == 'BYE':
            # Call ended by remote party
            logger.info("Call terminated by remote party")
            self.call_in_progress = False
            if self.rtp_handler:
                self.rtp_handler.stop()
    
    def cleanup(self):
        """Clean up resources"""
        if self.call_in_progress:
            self.end_call()
        
        if self.rtp_handler:
            self.rtp_handler.close()
        
        if self.sip_handler:
            self.sip_handler.close()

def caller_mode(args):
    """Run as caller"""
    client = VoIPClient(args.local_ip, args.local_sip_port, args.local_rtp_port)
    client.setup_handlers(args.remote_ip, args.remote_sip_port)
    
    try:
        # Initiate call
        client.initiate_call()
        
        # Wait for call to be established
        while not client.call_in_progress:
            time.sleep(0.1)
            
        # Wait a bit to ensure connection is stable
        logger.info("Call established, waiting before sending audio...")
        time.sleep(1)
        
        # Stream audio file
        client.stream_audio(args.audio_file)
        
        # Keep program running until streaming is done
        if client.rtp_handler:
            while not client.rtp_handler.stream_complete:
                time.sleep(0.5)
            
            # Wait a bit before ending call
            time.sleep(1)
        
        # End call
        client.end_call()
        time.sleep(1)  # Give time for BYE to be sent
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        client.cleanup()

def receiver_mode(args):
    """Run as receiver"""
    client = VoIPClient(args.local_ip, args.local_sip_port, args.local_rtp_port)
    client.setup_handlers(args.remote_ip, args.remote_sip_port)
    
    try:
        logger.info(f"Listening for incoming calls on {args.local_ip}:{args.local_sip_port}")
        
        # Keep program running until interrupted
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        client.cleanup()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VoIP Client with SIP and RTP")
    
    parser.add_argument("--local-ip", default="127.0.0.1", help="Local IP address")
    parser.add_argument("--local-sip-port", type=int, default=5060, help="Local SIP port")
    parser.add_argument("--local-rtp-port", type=int, default=10000, help="Local RTP port")
    parser.add_argument("--remote-ip", default="127.0.0.1", help="Remote IP address")
    parser.add_argument("--remote-sip-port", type=int, default=5061, help="Remote SIP port")
    parser.add_argument("--mode", choices=["caller", "receiver"], default="receiver",
                        help="Run as caller or receiver")
    parser.add_argument("--audio-file", default="sample.wav", help="Audio file to stream (caller only)")
    
    args = parser.parse_args()
    
    if args.mode == "caller":
        caller_mode(args)
    else:
        receiver_mode(args)