import json, os, subprocess, time, datetime, shutil

H = os.path.expanduser("~")
CONF = H + "/nova_config.json"
ETAT = H + "/nova_veille_etat.json"
INTERVALLE = 900

def lire(f, defaut):
    try:
        with open(f) as fh:
            return json.load(fh)
    except Exception:
        return defaut

def ecrire(f, d):
    with open(f, "w") as fh:
        json.dump(d, fh)

def parler(texte):
    print(f"[{datetime.datetime.now():%H:%M}] Nova (veille) :", texte, flush=True)
    subprocess.run(["termux-tts-speak", "-l", "fr", texte])

def lire_batterie():
    try:
        r = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=10)
        b = json.loads(r.stdout)
        charge = b.get("status") == "CHARGING" or str(b.get("plugged", "UNPLUGGED")).upper() != "UNPLUGGED"
        return b["percentage"], charge
    except Exception:
        return None

def disque_libre_go():
    return shutil.disk_usage(H)[2] / 10**9

def verifier_une_fois():
    etat = lire(ETAT, {"alerte_batterie": False, "alerte_stockage": False})
    b = lire_batterie()
    if b:
        pct, charge = b
        if charge or pct > 20:
            etat["alerte_batterie"] = False
        elif pct <= 15 and not etat["alerte_batterie"]:
            parler(f"Ta batterie est à {pct} pour cent, pense à charger.")
            etat["alerte_batterie"] = True
    lim = lire(CONF, {}).get("limite_go")
    if lim:
        libre = disque_libre_go()
        if libre > lim * 0.15:
            etat["alerte_stockage"] = False
        elif libre < lim * 0.1 and not etat["alerte_stockage"]:
            parler(f"Attention, il ne te reste que {libre:.1f} gigaoctets sur ta limite de {lim:g}.")
            etat["alerte_stockage"] = True
    ecrire(ETAT, etat)

def boucle():
    parler("Je passe en veille, je surveille ta batterie et ton stockage en arrière-plan.")
    while True:
        verifier_une_fois()
        time.sleep(INTERVALLE)

if __name__ == "__main__":
    boucle()
