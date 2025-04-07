import sys
from AudioClient_CoTan import AudioClient
import time

"""
VoIP Client Launcher

Usage:
    AudioLauncher.py <local_ip> <local_port> <remote_ip> <remote_port> <audio_file> <role>
    
Arguments:
    local_ip: IP address to bind to
    local_port: Port to listen on
    remote_ip: Remote endpoint IP
    remote_port: Remote endpoint port
    audio_file: Path to audio file to stream
    role: Either 'caller' or 'receiver'
"""

if __name__ == "__main__":
    if len(sys.argv) != 7:
        print("[Usage: AudioLauncher.py <local_ip> <local_port> <remote_ip> <remote_port> <audio_file> <role>]")
        print("Role must be either 'caller' or 'receiver'")
        sys.exit(1)
        
    local_ip = sys.argv[1]
    local_port = int(sys.argv[2])
    remote_ip = sys.argv[3]
    remote_port = int(sys.argv[4])
    audio_file = sys.argv[5]
    role = sys.argv[6]
    
    try:
        client = AudioClient(local_ip, local_port, remote_ip, remote_port, role)
        if role.lower() == 'caller':
            client.start_call(audio_file)
        else:
            print(f"Listening for incoming calls on {local_ip}:{local_port}")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        if 'client' in locals():
            client.cleanup()
