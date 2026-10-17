"""Stati di Bormuri. Il nome è anche la parola mandata alla Plasma (`S RIPOSO`)."""

from enum import Enum


class State(str, Enum):
    RIPOSO = "RIPOSO"      # respiro lento
    ASCOLTO = "ASCOLTO"    # scansione blu
    PENSIERO = "PENSIERO"  # arancio che rincorre
    PARLA = "PARLA"        # rosso che pulsa con la voce
    MUTO = "MUTO"          # microfono spento, luci al minimo
    RIUNIONE = "RIUNIONE"  # camera e microfono lasciati alla riunione, luce "in onda"
