import typer
from ipa_core.kernel import Kernel, KernelConfig
from ipa_core.plugins import list_plugins

app = typer.Typer(help="CLI microkernel IPA (skeleton)")

@app.command()
def plugins():
    typer.echo("ASR backends: " + ", ".join(list_plugins("ipa_core.backends.asr")))
    typer.echo("TextRef: " + ", ".join(list_plugins("ipa_core.plugins.textref")))
    typer.echo("Comparators: " + ", ".join(list_plugins("ipa_core.plugins.compare")))

@app.command()
def run(audio: str = typer.Argument(..., help="Ruta a audio WAV/otros"),
        text: str = typer.Argument(..., help="Frase de referencia (texto)"),
        asr: str = "null",
        textref: str = "noop",
        cmp: str = "noop",
        lang: str | None = None):
    k = Kernel(KernelConfig(asr=asr, textref=textref, comparator=cmp))
    ipa_spk = k.audio_to_ipa(audio)
    ipa_ref = k.text_to_ipa(text, lang)
    res = k.compare(ipa_ref, ipa_spk)

    typer.echo(f"IPA_sistema : {ipa_ref}")
    typer.echo(f"IPA_hablante: {ipa_spk}")
    typer.echo(f"PER: {res.per:.3f}")
    if res.ops:
        typer.echo("Ops:")
        for op, r, h in res.ops:
            typer.echo(f"{op:3s} | ref='{r}' hyp='{h}'")
