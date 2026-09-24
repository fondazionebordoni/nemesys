# Test: il servizio NeMeSys si arresta dopo il riavvio

Obiettivo: capire se l'arresto del servizio dopo il riavvio di Windows è
causato da un bug nel codice (timing/dipendenze al boot, eccezione non
gestita) oppure da un blocco di sistema legato alla mancanza di firma del
pacchetto (Smart App Control, Windows Defender).

Il codice in `nemesys/Nemesys.py` è già stato modificato per loggare un
traceback completo se `SvcDoRun` va in crash, quindi il test è decisivo:
se il log riporta "started" seguito dal traceback, il processo è partito
ed è poi crashato (bug nel codice, non blocco di sistema); se il log è
vuoto, il processo non è mai partito (probabile blocco a monte).

## 1. Build del pacchetto

```
python setup_win.py
```

Poi compila l'installer con Inno Setup (GUI oppure `ISCC.exe nemesys.iss`).

## 2. Installazione

Installa il pacchetto generato normalmente, **senza firmarlo** (è voluto
per questo test).

## 3. Riavvio

Riavvia la macchina e **aspetta almeno 5 minuti** prima di controllare.
Il delayed start del servizio parte circa 1-2 minuti dopo il boot, e se
fallisce, i 3 tentativi di retry configurati in `Nemesys.py`
(`_set_failure_actions`, 60s l'uno) devono fare in tempo a esaurirsi prima
che lo stato si stabilizzi su "Arrestato".

## 4. Stato del servizio

```powershell
Get-Service NeMeSys
```

Se risulta `Stopped`, procedi al punto 5.

## 4bis. Controllo configurazione di recovery del servizio

```powershell
sc.exe qfailure NeMeSys
```

Verifica che le azioni di ripristino risultino configurate (3x
`RESTART` con delay 60000ms). Se invece mostra "Nessuna azione" /
`NONE`, la configurazione di recovery (`_set_failure_actions` in
`Nemesys.py`) non è stata applicata correttamente — in questo caso il
servizio si ferma al primo crash senza mai riprovare, a prescindere
dalla causa iniziale. È un bug indipendente, da correggere comunque.

## 5. Controllo del log NeMeSys (passo decisivo)

```powershell
Get-WinEvent -LogName Application -MaxEvents 50 |
    Where-Object { $_.ProviderName -like "*NeMeSys*" } |
    Format-List TimeCreated, Message
```

- **C'è la riga "NeMeSys Service - started" seguita da un traceback
  Python?** → il processo è partito ed è crashato dopo: è un bug nel
  codice, non un blocco di sistema. Recuperare il traceback completo.
- **Non c'è nessuna riga, nemmeno "started"?** → il processo non è mai
  partito. Passare al punto 6.

## 6. Solo se il punto 5 è vuoto: controllo blocco a monte

```powershell
Get-WinEvent -LogName System -MaxEvents 50 |
    Where-Object { $_.ProviderName -eq "Service Control Manager" -and $_.Message -like "*NeMeSys*" } |
    Format-List TimeCreated, Id, Message
```

E in parallelo, più leggibile: **Sicurezza di Windows → Protezione da
virus e minacce → Cronologia protezione** — qui compaiono sia i
rilevamenti di Windows Defender sia i blocchi di Smart App Control, con
timestamp. Cercare un evento vicino all'orario del riavvio.

## Interpretazione dei risultati

| Osservazione | Conclusione |
|---|---|
| Log NeMeSys con "started" + traceback | Bug nel codice (timing/dipendenze/eccezione), non serve la firma per risolvere questo problema |
| Log NeMeSys vuoto + evento SCM di errore | Il processo non è mai partito: possibile problema di dipendenze del servizio (`EventSystem`, `Tcpip`, `Netman`, `EventLog`) o blocco a monte |
| Log NeMeSys vuoto + evento in Cronologia protezione (Smart App Control) | Blocco di sistema legato alla mancanza di firma: qui la firma del pacchetto è la soluzione |

## Nota sul contesto

Il target di distribuzione è PC di utenti comuni ("persone normali"), non
macchine aziendali con policy IT. Questo esclude WDAC/Device Guard (solo
enterprise) ma **non** esclude Smart App Control, che su installazioni
pulite di Windows 11 si attiva di default dopo una settimana di
valutazione. Anche se questo test escludesse Smart App Control come causa
di *questo* arresto specifico, procurarsi un certificato di code signing
resta comunque raccomandato per il contesto di distribuzione consumer.
