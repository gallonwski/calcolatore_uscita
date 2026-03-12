# Investment Decision Dashboard
## Logica dei calcoli e struttura del modello

Questo progetto implementa una dashboard in Streamlit per analizzare un piano di investimento con versamenti periodici e valutare l'impatto economico di un'uscita anticipata.

L'obiettivo della dashboard è confrontare tre elementi:

1. il valore finale del piano se l'investimento resta attivo fino alla scadenza
2. il valore finale di uno scenario alternativo in caso di uscita anticipata e reinvestimento
3. il valore di crescita composta futura che viene perso interrompendo il piano prima del termine

---

# 1. Obiettivo del modello

La dashboard è stata progettata per rispondere a due domande principali:

- **quanto vale il piano se viene mantenuto fino alla fine**
- **quanto valore futuro si rinuncia a catturare se si esce prima**

Il focus non è soltanto il costo esplicito dell'uscita, come la penale. Il punto centrale è soprattutto la perdita del compounding, cioè della crescita futura che il capitale avrebbe potuto generare restando investito più a lungo.

---

# 2. Input principali

La simulazione utilizza i seguenti input:

- **Investimento iniziale**
- **Versamento mensile**
- **Rendimento annuo atteso**
- **Durata del piano in anni**
- **Anno di uscita anticipata**
- **Penale di uscita**, espressa come percentuale del capitale versato fino a quel momento
- **Altri costi di uscita**
- **Rendimento annuo del nuovo investimento**
- **Livello di incertezza**
- **Numero di simulazioni Monte Carlo**

---

# 3. Logica del piano di accumulo

## 3.1 Struttura del calcolo

Il piano viene simulato mese per mese.

Per ogni mese il saldo evolve in base a:

1. rendimento del capitale già investito
2. aggiunta del versamento mensile

La dashboard usa la convenzione standard di **versamento a fine periodo**, quindi la logica del mese è:

```python
saldo = saldo * (1 + rendimento_mensile) + versamento_mensile
