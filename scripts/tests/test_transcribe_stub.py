# Test: transcribe pipeline with stubs
from ipa_core.pipeline.transcribe import transcribe
from ipa_core.preprocessor_basic import BasicPreprocessor
from ipa_core.backends.asr_stub import StubASR
from typing import Protocol
class _TR(Protocol):
  def to_ipa(self,text:str,*,lang:str,**kw)->list[str]:...
class SimpleTR:
  def to_ipa(self,text:str,*,lang:str,**kw):
    return list(text.replace(" ",""))
if __name__=="__main__":
  pre=BasicPreprocessor()
  asr=StubASR({"stub_tokens":["h","o","l","a"]})
  tokens=transcribe(pre,asr,SimpleTR(),audio={"path":"inputs/rec.wav","sample_rate":16000,"channels":1},lang="es")
  print("TOKENS:",tokens, "STR:"," ".join(tokens))
