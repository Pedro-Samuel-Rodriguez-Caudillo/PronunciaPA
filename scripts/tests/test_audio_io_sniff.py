# Test: audio_io sniff WAV
from ipa_core.backends.audio_io import sniff_wav,to_audio_input
import sys
if __name__=="__main__":
  p=sys.argv[1] if len(sys.argv)>1 else "inputs/rec.wav"
  info=sniff_wav(p)
  ai=to_audio_input(p)
  print("OK",info,ai)
