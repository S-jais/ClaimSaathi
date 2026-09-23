import urllib.request
import json

def test_endpoints():
    # 1. Config endpoint
    req = urllib.request.Request('http://127.0.0.1:8000/api/v1/voice/config')
    with urllib.request.urlopen(req) as resp:
        print('CONFIG STATUS:', resp.status)
        config = json.loads(resp.read().decode('utf-8'))
        print('CONFIG BODY:', config)
        assert config['enabled'] is True

    # 2. Spoken transformation + Speak endpoint (returns audio/wav binary stream)
    text = "नमस्ते Siddhartha, आपका क्लेम ₹45,000 का अंडर रिव्यू है। पॉलिसी 12345678 है।"
    speak_req = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/voice/speak', 
        data=json.dumps({'text': text, 'language': 'hi', 'voice': 'Puck'}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(speak_req) as resp:
        wav_bytes = resp.read()
        print('SPEAK STATUS:', resp.status)
        print('CONTENT TYPE:', resp.headers.get('content-type'))
        print('AUDIO SIZE (BYTES):', len(wav_bytes))
        print('RIFF HEADER:', wav_bytes[:4])
        assert resp.status == 200
        assert resp.headers.get('content-type') == 'audio/wav'
        assert wav_bytes[:4] == b'RIFF'
        print('>>> Speak endpoint streaming verified successfully!')

    # 3. Test Canned Phrase
    canned_req = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/voice/speak', 
        data=json.dumps({'text': 'नमस्ते, मैं क्लेम साथी हूँ। मैं आपकी क्या मदद कर सकता हूँ?', 'language': 'hi'}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(canned_req) as resp:
        canned_bytes = resp.read()
        print('CANNED SPEAK STATUS:', resp.status)
        print('CANNED AUDIO SIZE:', len(canned_bytes))
        assert canned_bytes[:4] == b'RIFF'
        print('>>> Canned phrase verified successfully!')

if __name__ == '__main__':
    test_endpoints()
