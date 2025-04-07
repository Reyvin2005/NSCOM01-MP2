# Real-Time Audio Streaming over IP

This project implements a simplified VoIP application that uses SIP for signaling and RTP for media transport. The implementation focuses on audio streaming between two clients, without requiring a SIP proxy.

---

## Features

- **SIP Signaling**:
  - Handles `INVITE`, `ACK`, `BYE`, and `200 OK` messages for call setup and teardown.
  - Includes SDP (Session Description Protocol) for media negotiation.
- **RTP Streaming**:
  - Streams audio data over RTP using G.711 (PCMU) codec.
  - Supports real-time playback on the receiving end.
- **RTCP Reporting**:
  - Periodically sends and receives RTCP packets for stream statistics (e.g., packet count, jitter).
- **Audio Playback and Conversion**:
  - Supports `.wav` files with mono, 16-bit PCM encoding, and 8000 Hz sample rate.
  - Converts unsupported audio formats to the required format using `scipy` and `soundfile`.
- **Error Handling**:
  - Gracefully handles SIP errors (e.g., `4xx`, `5xx` responses).
  - Logs and recovers from unexpected RTP/RTCP packet issues.
  - Ensures the application does not crash on invalid inputs or network errors.

---

## Requirements

- **Python Version**: Python 3.7+
- **Dependencies**:
  - `pyaudio` (for audio playback and recording)
  - `scipy` (for audio resampling)
  - `soundfile` (for audio format conversion)
  - `numpy` (for audio data manipulation)

### Installing Dependencies

Run the following command to install the required Python packages:

```bash
pip install pyaudio scipy soundfile numpy
```

---

## Usage

### Running the Receiver

The receiver listens for incoming SIP calls and plays the received audio in real-time.

```bash
python AudioLauncher_CoTan.py <local_ip> <local_port> <remote_ip> <remote_port> <audio_file> receiver
```

Examples:

```bash
# Local testing (Receiver on localhost)
python AudioLauncher_CoTan.py 127.0.0.1 5061 127.0.0.1 5060 sample.wav receiver

# Local Host A (Receiver)
python AudioLauncher_CoTan.py 127.0.0.1 5060 127.0.0.1 5070 dummy.wav receiver

# On Host A (Receiver) - Different networks
python AudioLauncher_CoTan.py <Host_A_IP> 5060 <Host_B_IP> 5070 dummy.wav receiver
```

### Running the Caller

The caller initiates a SIP call and streams the specified audio file to the receiver.

```bash
python AudioLauncher_CoTan.py <local_ip> <local_port> <remote_ip> <remote_port> <audio_file> caller
```

Examples:

```bash
# Local testing (Caller on localhost)
python AudioLauncher_CoTan.py 127.0.0.1 5060 127.0.0.1 5061 sample.wav caller

# Local Host B (Caller)
python AudioLauncher_CoTan.py 127.0.0.1 5070 127.0.0.1 5060 your_audio.wav caller

# On Host B (Caller) - Different networks
python AudioLauncher_CoTan.py <Host_B_IP> 5070 <Host_A_IP> 5060 your_audio.wav caller
```

---

## Test Cases

### Test Case 1: Localhost Communication

1. Start the receiver:
   ```bash
   python AudioLauncher_CoTan.py 127.0.0.1 5061 127.0.0.1 5060 sample.wav receiver
   ```
2. Start the caller:
   ```bash
   python AudioLauncher_CoTan.py 127.0.0.1 5060 127.0.0.1 5061 sample.wav caller
   ```
3. Expected Output:
   - The receiver plays the audio file in real-time.
   - Both the caller and receiver log SIP messages (`INVITE`, `200 OK`, `ACK`, `BYE`) and RTP/RTCP statistics.

### Test Case 2: Alternative Port Configuration

1. Start the receiver:
   ```bash
   python AudioLauncher_CoTan.py 127.0.0.1 5070 127.0.0.1 5060 audio.wav receiver
   ```
2. Start the caller:
   ```bash
   python AudioLauncher_CoTan.py 127.0.0.1 5060 127.0.0.1 5070 audio.wav caller
   ```
3. Expected Output:
   - Same behavior as Test Case 1, but using different port numbers.

### Test Case 3: Multi-Format Support

The application supports multiple audio formats with automatic conversion. Run the receiver:
```bash
python AudioLauncher_CoTan.py 127.0.0.1 5070 127.0.0.1 5060 audio.wav receiver
```

Then test with different audio formats:

1. **WAV format** (natively supported):
   ```bash
   python AudioLauncher_CoTan.py 127.0.0.1 5060 127.0.0.1 5070 Test_WAV.wav caller
   ```

2. **AIFF format** (automatically converted):
   ```bash
   python AudioLauncher_CoTan.py 127.0.0.1 5060 127.0.0.1 5070 Test_AIFF.aiff caller
   ```

3. **FLAC format** (automatically converted):
   ```bash
   python AudioLauncher_CoTan.py 127.0.0.1 5060 127.0.0.1 5070 Test_FLAC.flac caller
   ```

4. **MP3 format** (automatically converted):
   ```bash
   python AudioLauncher_CoTan.py 127.0.0.1 5060 127.0.0.1 5070 Test_MP3.mp3 caller
   ```

5. **OGG format** (automatically converted):
   ```bash
   python AudioLauncher_CoTan.py 127.0.0.1 5060 127.0.0.1 5070 Test_OGG.ogg caller
   ```

Expected Output:
- For non-WAV formats, the logs will show conversion process details
- All formats should stream and play correctly after conversion

### Test Case 4: Invalid Audio File

1. Run the caller with an unsupported audio file format:
   ```bash
   python AudioLauncher_CoTan.py 127.0.0.1 5060 127.0.0.1 5061 invalid.mp3 caller
   ```
2. Expected Output:
   - The application converts the file to `.wav` format and streams it successfully.
   - Logs indicate the conversion process.

### Test Case 5: Network Error

1. Disconnect the network or terminate the receiver during the call.
2. Expected Output:
   - The caller logs an error indicating the network issue.
   - The application does not crash and gracefully terminates the session.

---

## Sample Outputs

### Caller Output

```plaintext
[SIP] Sending INVITE to 127.0.0.1:5061
[SIP] Received 200 OK
[SIP] Sending ACK
[RTP] Starting audio stream to 127.0.0.1:10003
[RTP] Sending packet: 160 bytes (Sequence #1)
[RTP] Sending packet: 160 bytes (Sequence #2)
...
[RTCP Report Sent]
Total Packets: 100
Total Data Sent: 16,000 bytes
Average Bitrate: 64.0 kbps
[SIP] Sending BYE
```

### Receiver Output

```plaintext
[SIP] Received INVITE
[SIP] Sending 200 OK
[SIP] Received ACK
[Call] Session established - Ready to receive audio
[RTP] Received packet: 160 bytes (Sequence #1)
[RTP] Received packet: 160 bytes (Sequence #2)
...
[RTCP Report Received]
Total Packets: 100
Total Bytes: 16,000 bytes
[Call] Remote party ended the session
```

---

## Implementation Notes

1. **Audio Format**:
   - The application supports `.wav` files with mono, 16-bit PCM encoding, and 8000 Hz sample rate.
   - Other formats are automatically converted to the required format.
2. **SIP Protocol**:
   - The implementation includes basic SIP signaling for call setup and teardown.
   - No SIP proxy or registrar is required.
3. **RTP/RTCP**:
   - RTP is used for real-time audio streaming.
   - RTCP provides periodic statistics for monitoring stream quality.
4. **Error Handling**:
   - Handles invalid SIP messages, network errors, and unsupported audio formats gracefully.
   - Logs detailed error messages for debugging.

---

## Known Limitations

- NAT traversal is not supported (assumes both clients are on the same LAN).
- Audio encoding is limited to G.711 (PCMU).
- No advanced error recovery for dropped RTP packets.

---

## Project Structure

- `AudioLauncher_CoTan.py`: Entry point for the application.
- `AudioClient_CoTan.py`: Main VoIP client implementation.
- `SipPacket_CoTan.py`: SIP packet handling.
- `RtpPacket_CoTan.py`: RTP packet handling.
- `README.md`: Documentation.

---

## Protocol Flow

1. **Call Setup**:
   - Caller sends `INVITE` with SDP offering RTP port.
   - Receiver responds with `200 OK` and its own RTP port.
   - Caller acknowledges with `ACK`.
2. **Media Streaming**:
   - Audio flows via RTP from caller to receiver.
   - RTCP packets are exchanged periodically for statistics.
3. **Call Teardown**:
   - Either party sends `BYE` to terminate the session.
   - The other party responds with `200 OK`.

---

## Additional Notes

- Ensure the audio file is in the correct format or convertible, do not rename the file format as it will cause errors.
- Use the provided test cases to verify functionality.
- For debugging, check the logs for detailed SIP and RTP/RTCP messages.
