import os
import sys
import time
import subprocess
import threading

def run_receiver():
    """Run the client in receiver mode"""
    command = [
        "python", "client.py",
        "--mode", "receiver",
        "--local-ip", "127.0.0.1",
        "--local-sip-port", "5061",
        "--local-rtp-port", "10001",
        "--remote-ip", "127.0.0.1",
        "--remote-sip-port", "5060"
    ]
    
    receiver_process = subprocess.Popen(command)
    return receiver_process

def run_caller(audio_file):
    """Run the client in caller mode"""
    command = [
        "python", "client.py",
        "--mode", "caller",
        "--local-ip", "127.0.0.1",
        "--local-sip-port", "5060",
        "--local-rtp-port", "10000",
        "--remote-ip", "127.0.0.1",
        "--remote-sip-port", "5061",
        "--audio-file", audio_file
    ]
    
    caller_process = subprocess.Popen(command)
    return caller_process

def main():
    # Verify that audio file exists
    audio_file = "sample.wav"
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
    
    if not os.path.exists(audio_file):
        print(f"Error: Audio file '{audio_file}' not found.")
        print("Please provide a valid .wav file for streaming.")
        return
    
    print("Starting test...")
    print(f"1. Starting receiver (SIP port 5061, RTP port 10001)")
    receiver_process = run_receiver()
    
    # Give receiver time to start
    time.sleep(2)
    
    print(f"2. Starting caller with audio file: {audio_file}")
    caller_process = run_caller(audio_file)
    
    # Wait for caller to finish
    caller_process.wait()
    
    print("3. Stopping receiver...")
    receiver_process.terminate()
    
    print("Test complete!")

if __name__ == "__main__":
    main()