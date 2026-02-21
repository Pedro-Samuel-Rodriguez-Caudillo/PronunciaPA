import asyncio
from ipa_core.phonology.representation import PhonologicalRepresentation
from ipa_core.compare.compare import compare_representations
from ipa_core.pipeline.ipa_cleaning import clean_asr_tokens

async def debug():
    # Referencia: probando
    # En español: p - ɾ - o - β - a - n - d - o
    target = PhonologicalRepresentation.phonetic("pɾoβando")
    
    # Lo que el usuario dice que sale: prodento
    # p - ɾ - o - ð - e - n - t - o
    observed_raw = ["p", "ɾ", "o", "ð", "e", "n", "t", "o"]
    cleaned = clean_asr_tokens(observed_raw, lang="es")
    observed = PhonologicalRepresentation.phonetic("".join(cleaned))
    
    print(f"Target segments: {target.segments}")
    print(f"Observed segments: {observed.segments}")
    
    result = await compare_representations(target, observed, mode="objective")
    
    print(f"\nScore: {result.score}")
    print(f"PER: {result.distance / len(target.segments)}")
    print("Operations:")
    for op in result.operations:
        print(f"  {op}")

if __name__ == "__main__":
    asyncio.run(debug())
