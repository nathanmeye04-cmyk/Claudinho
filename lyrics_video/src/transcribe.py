import json, sys
from faster_whisper import WhisperModel
import wave, numpy as np
wf=wave.open("audio/mono16k.wav"); audio=np.frombuffer(wf.readframes(wf.getnframes()),dtype=np.int16).astype(np.float32)/32768
m = WhisperModel(sys.argv[1], device="cpu", compute_type="int8", cpu_threads=4)
segs, info = m.transcribe(audio, language="fr", word_timestamps=True, vad_filter=False, beam_size=5, condition_on_previous_text=False)
out=[]
for s in segs:
    print(f"{s.start:7.2f} {s.end:7.2f} {s.text}", flush=True)
    for w in s.words: out.append({"w":w.word.strip(),"s":round(w.start,3),"e":round(w.end,3),"p":round(w.probability,3)})
json.dump(out, open(f"whisper_words_{sys.argv[1]}.json","w"), ensure_ascii=False, indent=0)
