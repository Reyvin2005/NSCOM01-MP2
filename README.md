# Real-Time Audio Streaming over IP

This project implements a simplified VoIP application that uses SIP for signaling and RTP for media transport. The implementation focuses on audio streaming between two clients, without requiring a SIP proxy.

## Features

- SIP signaling (INVITE, ACK, BYE) for call setup and teardown
- RTP streaming of audio data
- Basic RTCP reports for statistics
- Real-time audio playback on the receiving end

## Requirements

- Python 3.7+
- PyAudio (`pip install pyaudio`)
- wave module (included in Python standard library)

### Installing PyAudio

PyAudio may require additional system dependencies:

**Windows:**
```
pip install pyaudio
```

**Linux:**
```
sudo apt-get install python3-pyaudio
# or
sudo apt-get install portaudio19-dev
pip install pyaudio
```

**macOS:**
```
brew install portaudio
pip install pyaudio
```

## Usage

### Running the Receiver

```bash
python client.py --mode receiver --local-ip 127.0.0.1 --local-sip-port 5061 --local-rtp-port 10001 --remote-ip 127.0.0.1 --remote-sip-port 5060
```

### Running the Caller

```bash
python client.py --mode caller --local-ip 127.0.0.1 --local-sip-port 5060 --local-rtp-port 10000 --remote-ip 127.0.0.1 --remote-sip-port 5061 --audio-file sample.wav
```

### Running the Test Script

For quick testing on a single machine:

```bash
python test.py sample.wav
```

## Audio File Format

The application is designed to work with:
- WAV files
- Mono (single channel)
- 16-bit PCM encoding
- 8000 Hz sample rate (for optimal G.711 compatibility)

## Project Structure

- `client.py` - Main VoIP client application
- `sip_handler.py` - SIP protocol implementation
- `rtp_handler.py` - RTP/RTCP implementation
- `test.py` - Helper script to test the application

## Implementation Notes

1. This is a simplified implementation focusing on the core protocols
2. No NAT traversal or complex error recovery
3. Audio encoding is basic (using raw PCM data rather than proper G.711)
4. Real deployments would use a more robust SIP stack

## Protocol Flow

1. Caller sends SIP INVITE with SDP offering RTP port
2. Receiver responds with 200 OK and its own RTP port
3. Caller acknowledges with ACK
4. Media flows via RTP until one side sends BYE
5. RTCP packets are exchanged periodically for statistics