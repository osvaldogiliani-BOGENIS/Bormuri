"""Scene luci per stato. Le animazioni girano sulla Plasma (firmware/plasma):
qui c'è solo la descrizione, per riferimento.

La ventola Noctua è alimentata da una porta USB dell'hub e gira a velocità fissa;
la Plasma legge la temperatura della base e, oltre 50 °C, dimezza i LED.
"""

from bormuri.state import State

SCENES = {
    State.RIPOSO: "respiro lento azzurro",
    State.ASCOLTO: "scansione blu",
    State.PENSIERO: "arancio che rincorre",
    State.PARLA: "rosso che pulsa con la voce",
    State.MUTO: "rosso fisso al minimo",
    State.RIUNIONE: "luce rossa 'in onda', il resto discreto",
}
