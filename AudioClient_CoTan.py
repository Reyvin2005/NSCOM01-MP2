import socket
import threading
import wave
import pyaudio
import time
import numpy as np
from scipy import signal
import soundfile as sf
import os
from SipPacket_CoTan import SipPacket
from RtpPacket_CoTan import RtpPacket

class AudioClient:
    """
    VoIP client implementation supporting audio streaming over RTP with SIP signaling.
    
    Features:
    - SIP-based call setup and teardown
    - RTP-based audio streaming
    - RTCP reporting for stream statistics
    - Multi-format audio file support
    - Real-time audio format conversion
    """
    
    CALLER = 0  # Role constant for call initiator
    RECEIVER = 1  # Role constant for call receiver

    def __init__(self, local_ip, local_port, remote_ip, remote_port, role='caller'):
        # Network setup
        self.local_ip = local_ip
        self.local_port = int(local_port)
        self.remote_ip = remote_ip
        self.remote_port = int(remote_port)
        
        # Session state
        self.call_id = str(int(time.time()))
        self.cseq = 0
        self.session_active = False
        self.is_receiving = False
        self.role = self.CALLER if role.lower() == 'caller' else self.RECEIVER

        # Audio configuration
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16  # Changed from paULaw to paInt16
        self.CHANNELS = 1
        self.RATE = 8000
        self.audio = pyaudio.PyAudio()
        
        # Statistics
        self.packets_sent = 0
        self.bytes_sent = 0
        self.start_time = 0
        
        # Setup network sockets
        self.sip_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sip_socket.settimeout(1.0)  # 1 second timeout
        self.sip_socket.bind((self.local_ip, self.local_port))
        print(f"\n[SIP] Server listening on {self.local_ip}:{self.local_port}")
        
        self.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtp_port = self.local_port + 2
        self.rtp_socket.bind((self.local_ip, self.rtp_port))
        
        # Start listening thread
        self.listen_thread = threading.Thread(target=self._listen_sip)
        self.listen_thread.daemon = True
        self.listen_thread.start()

        # Setup RTCP
        self._setup_rtcp()

    def _setup_rtcp(self):
        """Setup RTCP socket and start RTCP thread"""
        self.rtcp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtcp_port = self.rtp_port + 1
        self.rtcp_socket.bind((self.local_ip, self.rtcp_port))
        print(f"[RTCP] Control channel established on port {self.rtcp_port}")
        
        # Start RTCP sender thread
        self.rtcp_thread = threading.Thread(target=self._rtcp_reporter)
        self.rtcp_thread.daemon = True
        self.rtcp_thread.start()
        
        # Start RTCP receiver thread
        self.rtcp_receiver_thread = threading.Thread(target=self._rtcp_receiver)
        self.rtcp_receiver_thread.daemon = True
        self.rtcp_receiver_thread.start()

    def _rtcp_receiver(self):
        """Listen for incoming RTCP packets"""
        self.rtcp_socket.settimeout(1.0)
        while self.session_active:
            try:
                data, addr = self.rtcp_socket.recvfrom(1500)
                if data:
                    # Parse RTCP packet
                    version = (data[0] >> 6) & 0x03
                    packet_type = data[1] & 0xFF
                    length = (data[2] << 8 | data[3]) * 4 + 4
                    
                    if packet_type == 200:  # SR
                        ssrc = int.from_bytes(data[4:8], byteorder='big')
                        ntp_msw = int.from_bytes(data[8:12], byteorder='big')
                        ntp_lsw = int.from_bytes(data[12:16], byteorder='big')
                        rtp_ts = int.from_bytes(data[16:20], byteorder='big')
                        pkts = int.from_bytes(data[20:24], byteorder='big')
                        octets = int.from_bytes(data[24:28], byteorder='big')
                        
                        print("\n[RTCP Report Received]")
                        print("─" * 40)
                        print(f"Session ID: {ssrc}")
                        print(f"Total Packets: {pkts}")
                        print(f"Total Bytes: {octets:,} bytes")
                        print(f"Timestamp: {rtp_ts}")
                        print("─" * 40)
                    
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error receiving RTCP: {e}")

    def _rtcp_reporter(self):
        """Periodically send RTCP Sender Reports"""
        last_report_time = 0
        
        while self.session_active:
            try:
                current_time = time.time()
                if current_time - last_report_time >= 5:  # Send report every 5 seconds
                    if self.packets_sent > 0 or hasattr(self, 'packets_received'):
                        ntp_timestamp = int(current_time)
                        rtp_timestamp = int(current_time * self.RATE)
                        
                        # RTCP Header and Sender Info
                        header = bytearray(8)
                        header[0] = 0x80
                        header[1] = 200
                        length = 6
                        header[2] = (length >> 8) & 0xFF
                        header[3] = length & 0xFF
                        header[4:8] = int(self.call_id).to_bytes(4, byteorder='big')
                        
                        sender_info = bytearray(20)
                        sender_info[0:4] = (ntp_timestamp >> 32).to_bytes(4, byteorder='big')
                        sender_info[4:8] = (ntp_timestamp & 0xFFFFFFFF).to_bytes(4, byteorder='big')
                        sender_info[8:12] = rtp_timestamp.to_bytes(4, byteorder='big')
                        sender_info[12:16] = self.packets_sent.to_bytes(4, byteorder='big')
                        sender_info[16:20] = self.bytes_sent.to_bytes(4, byteorder='big')
                        
                        rtcp_packet = bytes(header) + bytes(sender_info)
                        self.rtcp_socket.sendto(rtcp_packet, (self.remote_ip, self.remote_port + 1))
                        
                        print("\n[RTCP Report Sent]")
                        print("─" * 40)
                        print(f"Time: {time.strftime('%H:%M:%S')}")
                        print(f"Total Packets: {self.packets_sent:,}")
                        print(f"Total Data Sent: {self.bytes_sent:,} bytes")
                        print(f"Session Duration: {current_time - self.start_time:.1f} seconds")
                        print(f"Average Bitrate: {(self.bytes_sent * 8) / (current_time - self.start_time) / 1000:.1f} kbps")
                        print("─" * 40)
                        
                        last_report_time = current_time
                
                time.sleep(1)  # Check every second
                    
            except Exception as e:
                print(f"Error sending RTCP: {e}")
                time.sleep(1)

    def start_call(self, audio_file):
        """Initiate SIP call and start streaming audio"""
        try:
            # Create and send INVITE
            sdp = self._create_sdp()
            packet = SipPacket()
            packet.create_invite(self.local_ip, self.remote_ip, 
                               self.call_id, self.cseq, sdp)
            
            self.sip_socket.sendto(packet.encode(), 
                                 (self.remote_ip, self.remote_port))
            
            # Wait for call setup
            while not self.session_active:
                time.sleep(0.1)
            
            # Start streaming audio
            self._stream_audio(audio_file)
            
        except Exception as e:
            print(f"Error starting call: {e}")
            self.cleanup()
            
    def _create_sdp(self):
        """Create SDP content for INVITE"""
        sdp = "v=0\r\n"
        sdp += f"o=- {self.call_id} 1 IN IP4 {self.local_ip}\r\n"
        sdp += "s=Audio Call\r\n"
        sdp += f"c=IN IP4 {self.local_ip}\r\n"
        sdp += "t=0 0\r\n"
        sdp += f"m=audio {self.rtp_port} RTP/AVP 0\r\n"  # 0 = PCMU
        sdp += "a=rtpmap:0 PCMU/8000\r\n"
        return sdp

    def _convert_audio_format(self, wf):
        """Convert audio to required format (mono, 8kHz, 16-bit)"""
        import numpy as np
        from scipy import signal
        
        # Read all frames from wave file
        frames = wf.readframes(wf.getnframes())
        
        # Convert to numpy array
        samples = np.frombuffer(frames, dtype=np.int16)
        
        # Convert stereo to mono if needed
        if wf.getnchannels() == 2:
            samples = samples.reshape(-1, 2)
            samples = samples.mean(axis=1)
        
        # Resample to 8kHz if needed
        if wf.getframerate() != self.RATE:
            samples = signal.resample(samples, 
                                    int(len(samples) * self.RATE / wf.getframerate()))
        
        # Convert back to 16-bit PCM
        return samples.astype(np.int16).tobytes()

    def _validate_and_convert_audio(self, audio_file):
        """Validate and convert audio file to WAV format if needed."""
        try:
            supported_formats = ('.wav', '.mp3', '.ogg', '.flac', '.aif', '.aiff')
            file_ext = os.path.splitext(audio_file)[1].lower()
            
            # Check if file exists
            if not os.path.exists(audio_file):
                raise FileNotFoundError(f"Audio file '{audio_file}' not found")
                
            # Check if format is supported    
            if file_ext not in supported_formats:
                raise ValueError(f"Unsupported audio format. Supported formats: {', '.join(supported_formats)}")
            
            print(f"\n[Audio] Processing file: {audio_file}")
            
            # Convert non-WAV files to WAV format
            if file_ext != '.wav':
                try:
                    print(f"[Audio] Converting {file_ext} file to WAV format...")
                    
                    # Read audio file with soundfile
                    data, sample_rate = sf.read(audio_file)
                    
                    # Convert to mono if stereo
                    if len(data.shape) > 1:
                        print("[Audio] Converting stereo to mono...")
                        data = np.mean(data, axis=1)
                    
                    # Resample if needed
                    if sample_rate != self.RATE:
                        print(f"[Audio] Resampling from {sample_rate}Hz to {self.RATE}Hz...")
                        samples = len(data)
                        data = signal.resample(data, int(samples * self.RATE / sample_rate))
                    
                    # Create temporary WAV file
                    temp_path = os.path.join(os.path.dirname(audio_file), 
                                           f"temp_{int(time.time())}.wav")
                    
                    # Save as 16-bit WAV
                    sf.write(temp_path, data, self.RATE, subtype='PCM_16')
                    print(f"[Audio] Converted file saved as: {temp_path}")
                    return temp_path, True
                    
                except Exception as e:
                    raise Exception(f"Error converting audio file: {str(e)}")
            
            return audio_file, False
            
        except Exception as e:
            raise Exception(f"Error processing audio file: {str(e)}")

    def _stream_audio(self, audio_file):
        """Read audio file and stream via RTP"""
        temp_file_created = False
        try:
            # Convert audio file if needed
            audio_file, temp_file_created = self._validate_and_convert_audio(audio_file)
            print(f"[Audio] Opening file for streaming: {audio_file}")
            
            wf = wave.open(audio_file, 'rb')
            
            # Print audio properties
            print("\n[Audio File Properties]")
            print("─" * 40)
            print(f"Format: WAV")
            print(f"Channels: {'Stereo' if wf.getnchannels() == 2 else 'Mono'}")
            print(f"Sample Rate: {wf.getframerate():,} Hz")
            print(f"Bit Depth: {wf.getsampwidth() * 8} bits")
            print(f"Duration: {wf.getnframes() / wf.getframerate():.1f} seconds")
            print("─" * 40)

            # Convert audio format if needed
            if wf.getnchannels() != self.CHANNELS or \
               wf.getframerate() != self.RATE or \
               wf.getsampwidth() != 2:  # 16-bit audio
                print("[Audio] Converting format to 8kHz mono...")
                audio_data = self._convert_audio_format(wf)
            else:
                audio_data = wf.readframes(wf.getnframes())
            
            # Split audio data into chunks
            chunk_size = self.CHUNK * 2  # 2 bytes per sample
            chunks = [audio_data[i:i+chunk_size] 
                     for i in range(0, len(audio_data), chunk_size)]
            
            self.start_time = time.time()
            seq_num = 0
            
            print(f"\n[RTP] Starting audio stream to {self.remote_ip}:{self.remote_port+2}")
            
            while self.session_active:
                for chunk in chunks:
                    if not self.session_active:
                        break
                        
                    # Create and send RTP packet
                    rtp_packet = RtpPacket()
                    rtp_packet.encode(2, 0, 0, 0, seq_num, 0, 0, 
                                    int(self.call_id), chunk)
                    
                    packet = rtp_packet.getPacket()
                    print(f"[RTP] Sending packet: {len(packet):,} bytes (Sequence #{seq_num})")
                    
                    self.rtp_socket.sendto(packet,
                                         (self.remote_ip, self.remote_port + 2))
                    
                    # Update statistics
                    self.packets_sent += 1
                    self.bytes_sent += len(chunk)
                    seq_num += 1
                    
                    # Control streaming rate
                    time.sleep(self.CHUNK / self.RATE)  # Sleep for chunk duration
                
                # Loop back to beginning when finished
                seq_num = 0
                
        except Exception as e:
            print(f"Error streaming audio: {e}")
        finally:
            if 'wf' in locals():
                wf.close()
            # Clean up temporary file if created
            if temp_file_created and os.path.exists(audio_file):
                try:
                    os.remove(audio_file)
                    print("[Audio] Cleaned up temporary conversion file")
                except:
                    pass

    def cleanup(self):
        """Clean up resources"""
        print("\n[System] Cleaning up resources")
        if self.session_active:
            self.send_bye()
            # Wait briefly for BYE response
            time.sleep(0.5)
        
        self.session_active = False
        if hasattr(self, 'audio'):
            self.audio.terminate()
        if hasattr(self, 'sip_socket'):
            self.sip_socket.close()
        if hasattr(self, 'rtp_socket'):
            self.rtp_socket.close()
        if hasattr(self, 'rtcp_socket'):
            self.rtcp_socket.close()
        print("[System] Closing network connections")

    def _listen_sip(self):
        """Listen for incoming SIP messages"""
        print(f"Listening for SIP messages on {self.local_ip}:{self.local_port}")
        
        while True:
            try:
                data, addr = self.sip_socket.recvfrom(2048)
                if data:
                    message = data.decode()
                    print(f"\nReceived SIP message:\n{message}")
                    
                    if message.startswith('INVITE'):
                        self._handle_invite(message, addr)
                    elif message.startswith('SIP/2.0 200'):
                        self._handle_ok(message)
                    elif message.startswith('BYE'):
                        self._handle_bye(addr)
                        
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error in SIP listener: {e}")
                if not self.session_active:
                    break

    def _handle_invite(self, message, addr):
        """Handle incoming INVITE request"""
        print("\n[SIP] Incoming call request received")
        if self.role == self.RECEIVER:
            # Extract SDP info
            lines = message.split('\n')
            for line in lines:
                if line.startswith('Call-ID:'):
                    self.call_id = line.split(':')[1].strip()
                elif line.startswith('CSeq:'):
                    self.cseq = int(line.split(':')[1].strip().split()[0])

            # Send 200 OK with SDP
            response = SipPacket()
            response.create_response(200)
            response.call_id = self.call_id
            response.cseq = self.cseq
            response.content_type = "application/sdp"
            response.content = self._create_sdp()
            
            self.sip_socket.sendto(response.encode(), addr)
            self.session_active = True
            print(f"[SIP] Call ID: {self.call_id}")
            print("[SIP] Sending acceptance (200 OK)")
            print("\n[Call] Session established - Ready to receive audio")
            
            # Start receiving audio
            self._start_receiving()

    def _start_receiving(self):
        """Start receiving and playing audio"""
        self.is_receiving = True
        threading.Thread(target=self._receive_audio).start()

    def _receive_audio(self):
        """Receive and play audio packets"""
        try:
            p = pyaudio.PyAudio()
            stream = p.open(format=self.FORMAT,
                           channels=self.CHANNELS,
                           rate=self.RATE,
                           output=True,
                           frames_per_buffer=self.CHUNK)
            
            print("\n[Audio] Starting playback - waiting for incoming stream...")
            self.rtp_socket.settimeout(0.5)
            
            packets_received = 0
            bytes_received = 0
            
            while self.is_receiving:
                try:
                    data, addr = self.rtp_socket.recvfrom(20480)
                    if data:
                        rtp_packet = RtpPacket()
                        rtp_packet.decode(data)
                        audio_data = rtp_packet.getPayload()
                        if audio_data:
                            packets_received += 1
                            bytes_received += len(audio_data)
                            print(f"[RTP] Received packet: {len(audio_data):,} bytes (Sequence #{rtp_packet.seqNum()})")
                            stream.write(audio_data)
                            
                            # Print RTCP stats every 50 packets
                            if packets_received % 50 == 0:
                                print(f"\nRTCP Statistics:")
                                print(f"Packets received: {packets_received}")
                                print(f"Bytes received: {bytes_received}")
                                print(f"Time elapsed: {time.time() - self.start_time:.2f}s")
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Error playing audio packet: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error in audio playback: {e}")
        finally:
            print("Cleaning up audio stream")
            if 'stream' in locals():
                stream.stop_stream()
                stream.close()
            if 'p' in locals():
                p.terminate()

    def _handle_ok(self, message):
        """Handle SIP OK response"""
        if self.role == self.CALLER:
            print(f"\n[SIP] Remote endpoint accepted call")
            # Parse SDP from response
            sdp_start = message.find('\r\n\r\n') + 4
            if sdp_start > 4:
                sdp = message[sdp_start:]
                
                # Extract remote RTP port from SDP
                for line in sdp.split('\n'):
                    if line.startswith('m=audio'):
                        remote_rtp_port = int(line.split()[1])
                        print(f"[RTP] Remote streaming port: {remote_rtp_port}")
                        break
                
                # Send ACK after processing 200 OK
                self._send_ack((self.remote_ip, self.remote_port))
                
                self.session_active = True
                self.start_time = time.time()
                print("[SIP] Sending acknowledgement (ACK)")
                print("\n[Call] Session established - Starting audio stream")

    def _handle_bye(self, addr):
        """Handle SIP BYE request"""
        print("\n[Call] Remote party ended the session")
        # Send 200 OK response
        response = SipPacket()
        response.create_response(200)
        self.sip_socket.sendto(response.encode(), addr)
        self.session_active = False
        self.is_receiving = False
        print("Call terminated by remote party")

    def send_bye(self):
        """Send BYE request to end call"""
        print("\n[Call] Ending session")
        self.cseq += 1
        bye_packet = SipPacket()
        bye_packet.method = "BYE"
        bye_packet.call_id = self.call_id
        bye_packet.cseq = self.cseq
        bye_packet.from_addr = self.local_ip
        bye_packet.to_addr = self.remote_ip
        
        self.sip_socket.sendto(bye_packet.encode(),
                              (self.remote_ip, self.remote_port))
        print("[SIP] Sending termination request (BYE)")

    def _send_ack(self, addr):
        """Send ACK for successful call setup"""
        self.cseq += 1
        ack_packet = SipPacket()
        ack_packet.method = "ACK"
        ack_packet.call_id = self.call_id
        ack_packet.cseq = self.cseq
        ack_packet.from_addr = self.local_ip
        ack_packet.to_addr = self.remote_ip
        
        self.sip_socket.sendto(ack_packet.encode(), addr)
        print("Sent ACK")