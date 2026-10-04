NOMS_APPS = {'com.whatsapp': 'WhatsApp', 'com.facebook.orca': 'Messenger', 'com.facebook.katana': 'Facebook', 'com.instagram.android': 'Instagram', 'com.google.android.youtube': 'YouTube', 'com.spotify.music': 'Spotify', 'com.tiktok': 'TikTok', 'org.telegram.messenger': 'Telegram', 'com.android.chrome': 'Chrome', 'com.google.android.apps.photos': 'Google Photos'}

import hashlib, subprocess, shutil, os, json, datetime, unicodedata, re, difflib, time

H = os.path.expanduser("~")
MEM, CONT, CONF, APPRIS, BATT = [H + "/nova_" + n + ".json" for n in ("memoire", "contacts", "config", "appris", "batterie")]
RACINE = H + "/storage/shared"
TYPES = {
    "musique": (".mp3", ".m4a", ".wav", ".flac", ".ogg", ".aac", ".opus"),
    "photos": (".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif"),
    "vidéos": (".mp4", ".mkv", ".3gp", ".avi", ".webm"),
    "apk": (".apk",),
    "documents": (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"),
}
JOURS = ["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"]
MOIS = ["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"]

def nettoyer(t):
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn").strip()

def fr(x):
    return str(int(x)) if x == int(x) else f"{x:.1f}".replace(".", ",")

def go(o):
    return fr(o / 10**9)

def parler(texte):
    print("Nova :", texte)
    subprocess.run(["termux-tts-speak", "-l", "fr", texte])

def lire(f, defaut):
    try:
        return json.load(open(f))
    except Exception:
        return defaut

def ecrire(f, d):
    json.dump(d, open(f, "w"))

def sonde(cmd, delai=8):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=delai)
    except Exception:
        return False
    texte = (r.stdout + r.stderr).lower()
    return r.returncode == 0 and "exception" not in texte and "denied" not in texte and "error" not in texte

def stockage():
    total, _, libre = shutil.disk_usage(H)
    lg = libre / 10**9
    lim = lire(CONF, {}).get("limite_go")
    if lim:
        pct = max(lim - lg, 0) * 100 / lim
        parler(f"Il te reste {fr(lg)} gigaoctets sur tes {fr(lim)} utilisables, soit {pct:.0f} pour cent utilisés.")
        if lg < lim * 0.1:
            parler("Attention, tu approches de ta limite.")
    else:
        parler(f"Il te reste {fr(lg)} gigaoctets sur {go(total)}. Dis : ma limite est 40 giga, pour que je retienne ta vraie limite.")

def verif_limite():
    lim = lire(CONF, {}).get("limite_go")
    if lim and shutil.disk_usage(H)[2] / 10**9 < lim * 0.1:
        parler("Attention, tu approches de ta limite de stockage.")

def regler_limite(p):
    m = re.search(r"\d+(?:[.,]\d+)?", p)
    c = lire(CONF, {})
    c["limite_go"] = float(m.group().replace(",", "."))
    ecrire(CONF, c)
    parler(f"C'est noté, ta limite est de {fr(c['limite_go'])} gigaoctets.")

def heure():
    n = datetime.datetime.now()
    parler(f"Il est {n.hour} heures {n.minute}.")

def date():
    n = datetime.datetime.now()
    parler(f"Nous sommes {JOURS[n.weekday()]} {n.day} {MOIS[n.month-1]} {n.year}.")

def batterie():
    try:
        r = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=10)
        b = json.loads(r.stdout)
        pct = b["percentage"]
        charge = b.get("status") == "CHARGING" or b.get("plugged", "UNPLUGGED") != "UNPLUGGED"
    except Exception:
        parler("Je ne peux pas lire la batterie pour l'instant.")
        return
    parler(f"Batterie à {pct} pour cent" + (", en charge." if charge else "."))
    if charge:
        ecrire(BATT, [])
        return
    now = time.time()
    mesures = lire(BATT, [])
    if mesures and pct > mesures[-1][1]:
        mesures = []
    mesures = [m for m in mesures if now - m[0] < 86400]
    mesures.append([now, pct])
    mesures = mesures[-50:]
    ecrire(BATT, mesures)
    t0, p0 = mesures[0]
    heures = (now - t0) / 3600
    chute = p0 - pct
    if heures >= 0.25 and chute >= 2:
        reste = pct / (chute / heures)
        h = int(reste)
        parler(f"À ce rythme, il te reste environ {h} heures {int((reste - h) * 60)} minutes d'autonomie.")
    else:
        parler("Je n'ai pas encore assez de mesures pour estimer l'autonomie. Redemande-moi un peu plus tard.")

def scanner():
    dossiers, lourds = {}, []
    for dossier, sous, liste in os.walk(RACINE):
        rel = os.path.relpath(dossier, RACINE)
        if rel == ".":
            sous[:] = [d for d in sous if d != "Android"]
        haut = "(racine)" if rel == "." else rel.split(os.sep)[0]
        for f in liste:
            chemin = os.path.join(dossier, f)
            try:
                t = os.path.getsize(chemin)
            except OSError:
                continue
            dossiers[haut] = dossiers.get(haut, 0) + t
            if t > 500 * 10**6:
                lourds.append((t, chemin))
    return dossiers, sorted(lourds, reverse=True)

def ecrire_lourds(liste):
    with open(H + "/nova_lourds.txt", "w") as out:
        for t, c in liste:
            print(f"{go(t)} Go | {c}", file=out)

def lourds():
    if not os.path.isdir(RACINE):
        parler("Je n'ai pas accès à tes fichiers.")
        return
    parler("Je cherche les fichiers de plus de 500 mégaoctets.")
    _, liste = scanner()
    ecrire_lourds(liste)
    if not liste:
        parler("Aucun fichier ne dépasse 500 mégaoctets.")
    else:
        total = sum(t for t, _ in liste)
        parler(f"J'ai trouvé {len(liste)} fichiers de plus de 500 mégaoctets, soit {go(total)} gigaoctets. Le plus gros fait {go(liste[0][0])} gigaoctets. La liste est dans nova lourds point t x t.")

def compter():
    res = {k: [0, 0] for k in TYPES}
    for dossier, sous, liste in os.walk(RACINE):
        sous[:] = [d for d in sous if not d.startswith(".") and d != "Android"]
        for f in liste:
            ext = os.path.splitext(f)[1].lower()
            for cat, exts in TYPES.items():
                if ext in exts:
                    res[cat][0] += 1
                    try:
                        res[cat][1] += os.path.getsize(os.path.join(dossier, f))
                    except OSError:
                        pass
                    break
    return res

def fichiers(p):
    if not os.path.isdir(RACINE):
        parler("Je n'ai pas accès à tes fichiers. Tape termux-setup-storage et autorise.")
        return
    parler("Je compte, un instant.")
    res = compter()
    cles = (("musique", "musique"), ("photo", "photos"), ("video", "vidéos"),
            ("apk", "apk"), ("document", "documents"))
    demandes = [cat for cle, cat in cles if cle in p] or list(TYPES)
    ph = [f"{res[c][0]} {c}, soit {go(res[c][1])} gigaoctets" for c in demandes]
    parler("Tu as " + ", ".join(ph) + ".")

def galerie():
    if not os.path.isdir(RACINE):
        parler("Je n'ai pas accès à tes fichiers.")
        return
    np = nv = taille = jour = 0
    dernier = 0
    auj = datetime.date.today()
    for base in ("DCIM", "Pictures"):
        for dossier, sous, liste in os.walk(os.path.join(RACINE, base)):
            sous[:] = [d for d in sous if not d.startswith(".")]
            for f in liste:
                ext = os.path.splitext(f)[1].lower()
                if ext not in TYPES["photos"] and ext not in TYPES["vidéos"]:
                    continue
                try:
                    st = os.stat(os.path.join(dossier, f))
                except OSError:
                    continue
                if ext in TYPES["photos"]:
                    np += 1
                else:
                    nv += 1
                taille += st.st_size
                dernier = max(dernier, st.st_mtime)
                if datetime.date.fromtimestamp(st.st_mtime) == auj:
                    jour += 1
    if np + nv == 0:
        parler("Je ne trouve rien dans ta galerie.")
        return
    d = datetime.date.fromtimestamp(dernier)
    parler(f"Ta galerie contient {np} photos et {nv} vidéos, soit {go(taille)} gigaoctets. La dernière date du {d.day} {MOIS[d.month-1]}. Aujourd'hui, tu en as ajouté {jour}.")

def applis():
    try:
        r = subprocess.run(["pm", "list", "packages", "-3"], capture_output=True, text=True, timeout=15)
        n = len([l for l in r.stdout.splitlines() if l.startswith("package:")])
        if n == 0:
            raise Exception
        parler(f"Tu as {n} applications installées par toi.")
    except Exception:
        parler("Android ne me laisse pas lister les applications depuis Termux.")

def doublons():
    if not os.path.isdir(RACINE):
        parler("Je n'ai pas accès à tes fichiers.")
        return
    parler("Je cherche les doublons, ça peut être long.")
    par_taille = {}
    for dossier, sous, liste in os.walk(RACINE):
        sous[:] = [d for d in sous if not d.startswith(".") and d != "Android"]
        for f in liste:
            chemin = os.path.join(dossier, f)
            try:
                t = os.path.getsize(chemin)
            except OSError:
                continue
            if t > 50000:
                par_taille.setdefault(t, []).append(chemin)
    groupes, perdu = 0, 0
    out = open(H + "/nova_doublons.txt", "w")
    for t, liste in par_taille.items():
        if len(liste) < 2:
            continue
        hashes = {}
        for c in liste:
            try:
                h = hashlib.md5()
                with open(c, "rb") as fh:
                    for bloc in iter(lambda: fh.read(1048576), b""):
                        h.update(bloc)
                hashes.setdefault(h.hexdigest(), []).append(c)
            except OSError:
                pass
        for l in hashes.values():
            if len(l) > 1:
                groupes += 1
                perdu += t * (len(l) - 1)
                print(*l, sep=" | ", file=out)
    out.close()
    auj = datetime.date.today()
    c = lire(CONF, {})
    c["doublons"] = {"groupes": groupes, "perdu": perdu, "date": f"{auj.day} {MOIS[auj.month-1]}"}
    ecrire(CONF, c)
    if groupes == 0:
        parler("Je n'ai trouvé aucun doublon.")
    else:
        parler(f"J'ai trouvé {groupes} fichiers en double, soit environ {go(perdu)} gigaoctets gaspillés. La liste est dans nova doublons point t x t.")

def limites():
    parler("Je fais le point sur ce que je peux et ne peux pas faire. Un instant.")
    acces = os.path.isdir(RACINE) and os.access(RACINE, os.R_OK)
    tests = [
        ("tes fichiers partagés", acces),
        ("la batterie", sonde(["termux-battery-status"])),
        ("tes contacts", sonde(["termux-contact-list"])),
        ("ton agenda", sonde(["content", "query", "--uri", "content://com.android.calendar/events", "--projection", "title"])),
        ("la liste des applications", sonde(["pm", "list", "packages", "-3"])),
    ]
    ok = [n for n, r in tests if r]
    non = [n for n, r in tests if not r] + ["tes alarmes"]
    parler("J'ai accès à : " + (", ".join(ok) if ok else "presque rien") + ".")
    parler("Je n'ai pas accès à : " + ", ".join(non) + ".")
    total, _, libre = shutil.disk_usage(H)
    utilise = max(total - libre, 1)
    parler(f"Ton téléphone a {go(total)} gigaoctets, dont {go(utilise)} utilisés.")
    lim = lire(CONF, {}).get("limite_go")
    if lim:
        parler(f"Ta limite d'utilisation fixée est de {fr(lim)} gigaoctets.")
    if acces:
        dossiers, liste = scanner()
        vu = sum(dossiers.values())
        parler(f"Les dossiers auxquels j'ai accès pèsent {go(vu)} gigaoctets, soit {vu * 100 / utilise:.0f} pour cent du stockage utilisé. Le reste, environ {go(max(utilise - vu, 0))} gigaoctets, est protégé : système, applications et leurs données.")
        top = sorted(dossiers.items(), key=lambda x: -x[1])[:3]
        if top:
            parler("Mes trois plus gros dossiers : " + ", ".join(f"{n} avec {go(t)} gigaoctets" for n, t in top) + ".")
        ecrire_lourds(liste)
        if liste:
            parler(f"Fichiers lourds : {len(liste)} dépassent 500 mégaoctets, soit {go(sum(t for t, _ in liste))} gigaoctets.")
        else:
            parler("Aucun fichier ne dépasse 500 mégaoctets.")
        d = lire(CONF, {}).get("doublons")
        if d:
            parler(f"Doublons : à ma dernière analyse du {d['date']}, {d['groupes']} fichiers en double, environ {go(d['perdu'])} gigaoctets gaspillés.")
        else:
            parler("Doublons : je n'ai pas encore fait d'analyse. Dis : doublons.")

def ajouter_contact(mots):
    i = mots.index("contact")
    if len(mots) < i + 3:
        parler("Dis : ajoute contact, le nom, puis le numéro.")
        return
    nom = mots[i + 1]
    num = "".join(c for c in "".join(mots[i + 2:]) if c.isdigit() or c == "+")
    c = lire(CONT, {})
    c[nom] = num
    ecrire(CONT, c)
    parler(f"Contact {nom} enregistré.")

def appel(p):
    for nom, num in lire(CONT, {}).items():
        if nom in p:
            parler(f"J'ouvre l'appel pour {nom}.")
            subprocess.run(["termux-open", f"tel:{num}"])
            return
    parler("Je ne connais pas ce contact.")

def retenir(p):
    info = p.split("retiens", 1)[1].strip()
    if info.startswith("que "):
        info = info[4:]
    m = lire(MEM, [])
    m.append(info)
    ecrire(MEM, m)
    parler("C'est noté.")

def rappeler():
    m = lire(MEM, [])
    parler("Je sais que " + ". ".join(m) if m else "Je ne sais encore rien.")

def resume():
    parler("Voici ton résumé.")
    heure()
    date()
    batterie()
    stockage()
    fichiers("")
    applis()

ACTIONS = {
    "heure": lambda p: heure(), "date": lambda p: date(),
    "batterie": lambda p: batterie(), "stockage": lambda p: stockage(),
    "fichiers": fichiers, "doublons": lambda p: doublons(),
    "lourds": lambda p: lourds(), "galerie": lambda p: galerie(),
    "limites": lambda p: limites(), "resume": lambda p: resume(),
    "applis": lambda p: applis(), "memoire": lambda p: rappeler(),
}

MOTS = [
    ("resume", ["resume", "bilan"]),
    ("doublons", ["doublon", "doublons", "double", "doubles"]),
    ("applis", ["appli", "applis", "application", "applications"]),
    ("lourds", ["lourd", "lourds", "gros", "volumineux"]),
    ("galerie", ["galerie", "gallery"]),
    ("fichiers", ["photo", "photos", "musique", "musiques", "video", "videos",
                  "apk", "document", "documents", "fichier", "fichiers"]),
    ("stockage", ["stockage", "espace", "memoire", "stocker"]),
    ("batterie", ["batterie", "charge", "pile", "autonomie"]),
    ("heure", ["heure", "horloge"]),
    ("date", ["date", "jour", "aujourd"]),
]

def proche(t, m):
    return t == m or (len(t) >= 4 and difflib.SequenceMatcher(None, t, m).ratio() >= 0.8)

def a_un(tokens, mots):
    return any(proche(t, m) for t in tokens for m in mots)

def apprendre(p):
    parler("Je n'ai pas compris. Que voulais-tu ? Regarde l'écran.")
    print("Choix :", ", ".join(ACTIONS), "| ou tape non")
    r = nettoyer(input("Toi : "))
    if r in ACTIONS:
        a = lire(APPRIS, {})
        a[p] = r
        ecrire(APPRIS, a)
        parler("D'accord, j'ai appris.")
        ACTIONS[r](p)
    else:
        parler("D'accord, on laisse tomber.")

def traiter(p):
    mots = p.split()
    t = [x for x in re.findall(r"[a-z0-9+]+", p) if x != "nova"]
    if a_un(t, ["media", "applis", "application", "applications", "apps"]) and a_un(t, ["espace", "stockage", "taille", "poids", "pesent", "occupent"]):
        espace_applis()
        return True
    if a_un(t, ["vide", "vider"]) and "corbeille" in t:
        vider_corbeille()
        return True
    if a_un(t, ["supprime", "supprimer", "efface", "effacer", "enleve", "enlever"]) and "doublon" in p:
        supprimer_doublons()
        return True
    if a_un(t, ["supprime", "supprimer", "efface", "effacer", "enleve", "enlever"]) and (
            a_un(t, ["lourd", "lourds", "gros", "grosse", "grosses", "volumineux", "volumineuse", "numero", "fichier", "fichiers"])):
        supprimer_lourds(p)
        return True
    if a_un(t, ["calcule", "calculer", "calcul", "calculette"]) or (
            (re.search(r"\d", p) or any(m in t for m in MOTS_NOMBRES)) and
            a_un(t, ["plus", "moins", "fois", "divise", "diviser", "combien", "fait", "font", "egal", "egale"])) or (
            re.fullmatch(r"[\d\s\.\+\-\*/x\(\)%,]+", p.strip()) and re.search(r"[\+\-\*/x%]", p) and re.search(r"\d", p)):
        calculette(p)
        return True
    if not t:
        return True
    if a_un(t, ["stop", "quitte", "quitter"]):
        parler("À bientôt.")
        return False
    if a_un(t, ["limite", "limites", "plafond"]):
        if re.search(r"\d", p):
            regler_limite(p)
        else:
            limites()
        return True
    appris = lire(APPRIS, {})
    voisin = difflib.get_close_matches(p, list(appris), n=1, cutoff=0.85)
    if voisin:
        ACTIONS[appris[voisin[0]]](p)
        return True
    if "contact" in t and a_un(t, ["ajoute", "ajouter", "enregistre"]):
        ajouter_contact(mots)
        return True
    if "appelle" in t or "appeler" in t:
        appel(p)
        return True
    if "retiens" in t:
        retenir(p)
        return True
    if ("que" in t and "sais" in t) or a_un(t, ["souviens", "souvenir"]):
        rappeler()
        return True
    for nom, cles in MOTS:
        if a_un(t, cles):
            ACTIONS[nom](p)
            return True
    cerveau(p)
    return True

OUI = ["oui", "ouais", "ouep", "ok", "okay", "yes", "go", "daccord", "accord", "confirme",
       "carrement", "exact", "voila", "top", "nickel", "banco", "parfait", "evidemment", "bien", "sur"]
NON = ["non", "nan", "nope", "annule", "jamais", "surtout", "stoppe", "laisse", "pas", "arrete"]

def confirmer(question):
    for i in range(2):
        parler(question)
        toks = re.findall(r"[a-z]+", nettoyer(input("Toi : ")))
        if not toks:
            continue
        if a_un(toks, NON):
            return False
        if a_un(toks, OUI) or ("vas" in toks and "y" in toks) or ("fais" in toks and "le" in toks):
            return True
        if i == 0:
            parler("Oui ou non ?")
    parler("Bon, je ne fais rien.")
    return False

def ajouter_contact(mots):
    p = " ".join(mots)
    m = re.search(r"\+?\d[\d\s.\-]{5,}\d", p)
    if not m:
        parler("Dis : ajoute contact, le nom, puis le numéro.")
        return
    num = re.sub(r"[^\d+]", "", m.group())
    ignorer = {"nova", "ajoute", "ajouter", "enregistre", "enregistrer", "cree", "creer", "contact", "contacts",
               "le", "la", "un", "une", "nomme", "appele", "numero", "de", "pour", "stp", "s", "il", "plait"}
    noms = [x for x in re.findall(r"[a-z]+", p[:m.start()]) if x not in ignorer]
    if not noms:
        parler("Je n'ai pas compris le nom du contact.")
        return
    nom = noms[-1]
    if confirmer(f"J'enregistre le contact {nom} avec le numéro {num}."):
        c = lire(CONT, {})
        c[nom] = num
        ecrire(CONT, c)
        parler(f"Contact {nom} enregistré.")
    else:
        parler("D'accord, je n'enregistre rien.")

def appel(p):
    contacts = lire(CONT, {})
    toks = [x for x in re.findall(r"[a-z0-9]+", p) if x != "nova"]
    nom = next((x for x in toks if x in contacts), None)
    if not nom:
        for x in toks:
            v = difflib.get_close_matches(x, list(contacts), n=1, cutoff=0.75)
            if v:
                nom = v[0]
                break
    if not nom:
        parler("Je ne connais pas ce contact.")
        return
    if confirmer(f"Je lance l'appel vers {nom}, au {contacts[nom]}."):
        subprocess.run(["termux-open", f"tel:{contacts[nom]}"])
    else:
        parler("D'accord, je n'appelle pas.")

def retenir(p):
    info = p.split("retiens", 1)[1].strip() if "retiens" in p else p
    info = re.sub(r"^(que|qu')\s*", "", info).strip()
    if not info:
        parler("Dis : retiens que, puis ce que je dois retenir.")
        return
    if confirmer(f"Je retiens : {info}."):
        m = lire(MEM, [])
        m.append(info)
        ecrire(MEM, m)
        parler("C'est noté.")
    else:
        parler("D'accord, j'oublie.")

def regler_limite(p):
    m = re.search(r"\d+(?:[.,]\d+)?", p)
    v = float(m.group().replace(",", "."))
    if confirmer(f"Je fixe ta limite à {fr(v)} gigaoctets."):
        c = lire(CONF, {})
        c["limite_go"] = v
        ecrire(CONF, c)
        parler("C'est noté.")
    else:
        parler("D'accord, je ne change rien.")

def bilan_simple():
    total, _, libre = shutil.disk_usage(H)
    utilise = max(total - libre, 0)
    cats = {k: 0 for k in TYPES}
    vu = 0
    acces = os.path.isdir(RACINE) and os.access(RACINE, os.R_OK)
    if acces:
        parler("Je fais le bilan, un instant.")
        for dossier, sous, liste in os.walk(RACINE):
            if dossier == RACINE:
                sous[:] = [d for d in sous if d != "Android"]
            for f in liste:
                try:
                    t = os.path.getsize(os.path.join(dossier, f))
                except OSError:
                    continue
                vu += t
                ext = os.path.splitext(f)[1].lower()
                for cat, exts in TYPES.items():
                    if ext in exts:
                        cats[cat] += t
                        break
    gris = max(utilise - vu, 0)
    base = max(vu + gris + libre, 1)
    autres = max(vu - sum(cats.values()), 0)
    lignes = [("APK" if k == "apk" else k.capitalize(), v, "█") for k, v in cats.items()]
    lignes += [("Autres", autres, "█"), ("Partie grise", gris, "▒"), ("Libre", libre, "░")]
    print("\n=== Bilan : 100% = tout ton stockage ===")
    for nom, v, car in lignes:
        pct = v * 100 / base
        n = round(pct * 14 / 100)
        aff = "<1%" if 0 < pct < 1 else f"{pct:.0f}%"
        print(f"{nom:<12} {car * n}{'.' * (14 - n)} {aff:>4}")
    print("█ analysé   ▒ non pris en charge   ░ libre\n")
    if not acces:
        parler("Je n'ai pas accès à tes fichiers, donc tout l'espace occupé est en partie grise. Tape termux-setup-storage et autorise.")
        return
    dits = [f"{v * 100 / base:.0f} pour cent {'autres fichiers' if nom == 'Autres' else nom.lower()}"
            for nom, v, car in lignes[:-2] if v * 100 / base >= 1]
    voix = "Sur cent pour cent de ton stockage : " + (", ".join(dits) if dits else "presque rien d'analysable") + ". "
    voix += f"La partie grise, {gris * 100 / base:.0f} pour cent, n'est pas prise en charge pour l'analyser. "
    voix += f"{libre * 100 / base:.0f} pour cent est libre. "
    voix += f"Je peux analyser {vu * 100 / max(utilise, 1):.0f} pour cent de l'espace occupé."
    parler(voix)

try:
    ACTIONS["bilan"] = lambda p: bilan_simple()
    MOTS.insert(0, ("bilan", ["bilan", "pourcentage", "pourcentages", "pourcent", "repartition", "statistique", "statistiques", "stats"]))
except NameError:
    pass

import random, builtins

DIAL = H + "/nova_dialogues.json"
DERNIER = [""]
_input_vrai = builtins.input

def _input_memoire(prompt=""):
    r = _input_vrai(prompt)
    DERNIER[0] = r
    return r

builtins.input = _input_memoire

PETIT = [
    ([{"salut"}, {"bonjour"}, {"coucou"}, {"hello"}, {"bonsoir"}, {"hey"}],
     ["Salut ! Je suis là.", "Coucou ! Contente de t'entendre.", "Bonjour ! Qu'est-ce que je peux faire pour toi ?"]),
    ([{"merci"}], ["Avec plaisir !", "De rien, c'est normal.", "Toujours là pour toi."]),
    ([{"ca", "va"}, {"comment", "vas"}, {"tu", "vas"}],
     ["Ça va très bien, merci ! Et toi ?", "Je vais bien, je suis prête à travailler. Et toi ?"]),
    ([{"qui", "es"}, {"ton", "nom"}, {"appelles"}, {"presente"}, {"presentes"}],
     ["Je m'appelle Nova. Je vis dans ton téléphone et j'apprends chaque jour."]),
    ([{"bonne", "nuit"}], ["Bonne nuit ! Repose-toi bien.", "Fais de beaux rêves, je garde le téléphone au chaud."]),
    ([{"blague"}, {"drole"}],
     ["Pourquoi les plongeurs plongent-ils toujours en arrière ? Parce que sinon ils tombent dans le bateau.",
      "Que fait une fraise sur un cheval ? Tagada, tagada.",
      "Qu'est-ce qu'un crocodile qui surveille une pharmacie ? Un Lacoste garde-malade."]),
    ([{"faire", "quoi"}, {"sais", "faire"}, {"peux", "faire"}, {"capacites"}, {"fonctions"}],
     ["Je te dis l'heure, la date, la batterie et ton stockage, je fais le bilan, je compte tes fichiers, "
      "je cherche les doublons, j'appelle tes contacts et je retiens des choses. "
      "Tu peux aussi m'entraîner à parler : dis mode entraînement."]),
    ([{"t", "aime"}], ["Moi aussi, je t'apprécie beaucoup."]),
    ([{"bravo"}, {"felicitations"}, {"genial"}], ["Merci, ça me fait très plaisir !"]),
]

def cle(p):
    return " ".join(x for x in re.findall(r"[a-z0-9]+", nettoyer(p)) if x != "nova")

def ajouter_dialogue(q, r):
    k, r = cle(q), r.strip()
    if not k or not r:
        return False
    d = lire(DIAL, {})
    d.setdefault(k, [])
    if r not in d[k]:
        d[k].append(r)
    ecrire(DIAL, d)
    return True

def reponse_apprise(p):
    d = lire(DIAL, {})
    k = cle(p)
    if not k or not d:
        return None
    if k in d:
        return random.choice(d[k])
    v = difflib.get_close_matches(k, list(d), n=1, cutoff=0.85)
    return random.choice(d[v[0]]) if v else None

def reponse_base(p):
    t = set(re.findall(r"[a-z0-9]+", p)) - {"nova"}
    if len(t) > 6:
        return None
    try:
        if any(a_un(list(t), cles) for _, cles in MOTS):
            return None
    except NameError:
        pass
    for groupes, reponses in PETIT:
        if any(g <= t for g in groupes):
            return random.choice(reponses)
    return None

def _ok(question):
    f = globals().get("confirmer")
    return f(question) if f else True

def entrainement():
    parler("Mode entraînement. Écris une phrase, puis ce que je dois répondre. Écris fin pour sortir.")
    fins = ("fin", "stop", "quitter", "termine", "terminer", "sortir")
    appris = 0
    while True:
        q = input("Phrase : ").strip()
        if nettoyer(q) in fins:
            break
        if not cle(q):
            continue
        r = input("Réponse : ").strip()
        if nettoyer(r) in fins:
            break
        if ajouter_dialogue(q, r):
            appris += 1
            parler(f"C'est appris. Quand tu dis {q}, je réponds : {r}")
    parler(f"Fin de l'entraînement. J'ai appris {appris} nouvelles choses.")

def lister_dialogues():
    d = lire(DIAL, {})
    if not d:
        parler("Je n'ai encore rien appris en conversation.")
        return
    for k, v in d.items():
        print(f"- {k}  ->  {' / '.join(v)}")
    parler(f"J'ai appris {len(d)} phrases. La liste est à l'écran.")

def oublier(t):
    d = lire(DIAL, {})
    i = t.index("oublie")
    reste = " ".join(t[i + 1:])
    v = difflib.get_close_matches(reste, list(d), n=1, cutoff=0.6) if reste else []
    if not v:
        parler("Je ne trouve pas cette phrase dans ce que j'ai appris.")
        return
    if _ok(f"J'oublie la phrase : {v[0]}."):
        del d[v[0]]
        ecrire(DIAL, d)
        parler("C'est oublié.")
    else:
        parler("D'accord, je garde.")

def apprendre(p):
    parler("Je ne sais pas encore répondre à ça. Écris ce que je dois répondre, ou le nom d'une action. Écris non pour passer.")
    print("Actions :", ", ".join(k for k in ACTIONS if k != "resume"))
    r = input("Toi : ").strip()
    n = nettoyer(r)
    if not n or n in ("non", "nan", "passe", "laisse tomber"):
        parler("D'accord, on laisse tomber.")
        return
    choix = n if n in ACTIONS else next(iter(difflib.get_close_matches(n, list(ACTIONS), n=1, cutoff=0.8)), None)
    if choix:
        a = lire(APPRIS, {})
        a[p] = choix
        ecrire(APPRIS, a)
        parler("D'accord, j'ai appris.")
        ACTIONS[choix](p)
    else:
        ajouter_dialogue(p, r)
        parler("Merci, je m'en souviendrai.")

_traiter_ancien = traiter

def traiter(p):
    brut = DERNIER[0]
    t = re.findall(r"[a-z0-9]+", p)
    m = re.search(r"(?:quand|si)\s+je\s+dis\s+(.+?)\s*,?\s+(?:tu\s+)?(?:r[ée]ponds?|dis)\s+(.+)", brut, re.I)
    if m and cle(m.group(1)):
        ajouter_dialogue(m.group(1), m.group(2))
        parler("C'est appris.")
        return True
    if a_un(t, ["entrainement", "entraine", "entrainer", "entrainons", "apprends", "apprendre"]):
        entrainement()
        return True
    if "oublie" in t:
        oublier(t)
        return True
    if "appris" in t and ("montre" in t or "liste" in t or "combien" in t or "quoi" in t or "qu" in t):
        lister_dialogues()
        return True
    rep = reponse_apprise(p) or reponse_base(p)
    if rep:
        parler(rep)
        return True
    return _traiter_ancien(p)

import urllib.request, urllib.error

CLE_FICHIER = H + "/.nova_cle"
MODELE_GEMINI = "gemini-3.8-flash"

def cle_gemini():
    try:
        return open(CLE_FICHIER).read().strip()
    except Exception:
        return ""

def cerveau(p):
    cle = cle_gemini()
    if not cle:
        parler("Je n'ai pas encore de clé pour réfléchir. Regarde le fichier point nova cle.")
        return
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELE_GEMINI}:generateContent"
    corps = json.dumps({
        "contents": [{"parts": [{"text": p}]}],
        "systemInstruction": {"parts": [{"text":
            "Tu es Nova, l'assistante vocale du téléphone de l'utilisateur. "
            "Réponds en français, en une ou deux phrases courtes, style oral, sans markdown ni listes."}]},
        "generationConfig": {"maxOutputTokens": 200}
    }).encode("utf-8")
    req = urllib.request.Request(url, data=corps, method="POST",
                                  headers={"Content-Type": "application/json", "x-goog-api-key": cle})
    for essai in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read())
            texte = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            parler(texte)
            return
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="ignore")[:200]
            if e.code in (503, 429) and essai < 2:
                time.sleep(3)
                continue
            parler("Ma clé ou ma connexion a un souci. Regarde l'écran pour le détail.")
            print("[erreur Gemini]", e.code, detail)
            return
        except Exception as e:
            parler("Je n'ai pas réussi à réfléchir, vérifie ta connexion internet.")
            print("[erreur]", e)
            return

import operator as _op

MOTS_NOMBRES = {"zero":0,"un":1,"une":1,"deux":2,"trois":3,"quatre":4,"cinq":5,"six":6,"sept":7,"huit":8,"neuf":9,
                "dix":10,"onze":11,"douze":12,"treize":13,"quatorze":14,"quinze":15,"seize":16,"vingt":20,
                "trente":30,"quarante":40,"cinquante":50,"soixante":60,"cent":100,"mille":1000}
MOTS_OPS = [
    (["plus", "additionne", "additionner", "ajoute", "somme"], "+"),
    (["moins", "soustrait", "soustraire", "retire", "retranche"], "-"),
    (["fois", "multiplie", "multiplier", "multiplication"], "*"),
    (["divise", "diviser", "division", "sur"], "/"),
    (["puissance", "exposant"], "**"),
]

def _mots_vers_operation(p):
    txt = p
    for mots, signe in MOTS_OPS:
        for m in mots:
            txt = re.sub(rf"\b{m}\b", f" {signe} ", txt)
    for mot, val in sorted(MOTS_NOMBRES.items(), key=lambda x: -len(x[0])):
        txt = re.sub(rf"\b{mot}\b", str(val), txt)
    return txt

def calculette(p):
    txt = p
    for mot in ("calcule", "calculer", "combien", "fait", "font", "egal", "egale", "resultat", "c'est", "cest", "de", "par", "est", "ca"):
        txt = re.sub(rf"\b{mot}\b", " ", txt)
    txt = _mots_vers_operation(txt)
    txt = txt.replace(",", ".").replace("x", "*").replace("÷", "/")
    if not re.fullmatch(r"[\d\s\.\+\-\*/\(\)%]+", txt.strip()) or not re.search(r"\d", txt):
        rep = probleme_simple(p)
        if rep:
            parler(rep)
        else:
            cerveau(p)
        return
    try:
        resultat = eval(txt, {"__builtins__": {}}, {})
    except ZeroDivisionError:
        parler("Impossible de diviser par zéro.")
        return
    except Exception:
        parler("Je n'ai pas réussi à calculer ça.")
        return
    if isinstance(resultat, float):
        resultat = round(resultat, 4)
        aff = f"{resultat:g}".replace(".", ",")
    else:
        aff = str(resultat)
    parler(f"Ça fait {aff}.")

UNITES = {"kg": "kilogrammes", "g": "grammes", "l": "litres", "km": "kilomètres", "m": "mètres",
          "kilo": "kilogrammes", "kilos": "kilogrammes", "gramme": "grammes", "grammes": "grammes",
          "litre": "litres", "litres": "litres", "kilometre": "kilomètres", "kilometres": "kilomètres",
          "metre": "mètres", "metres": "mètres", "franc": "francs", "francs": "francs",
          "dollar": "dollars", "dollars": "dollars", "personne": "personnes", "personnes": "personnes"}

def probleme_simple(p):
    txt = _mots_vers_operation(p)
    for mot in ("le", "la", "les", "de", "du", "des", "un", "une", "tout", "total", "ca", "c'est", "cest",
                "combien", "fait", "font", "egal", "egale", "sa", "sont", "vaut", "valent", "a"):
        txt = re.sub(rf"\b{mot}\b", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()

    segs = re.split(r"([\+\-])", txt)
    signe, total, unite, compte, ok = "+", 0.0, None, 0, False
    for seg in segs:
        seg = seg.strip()
        if seg in ("+", "-"):
            signe = seg
            continue
        if not seg:
            continue
        m = re.match(r"(\d+(?:[.,]\d+)?)\s*([a-zéèêà]*)\s*(?:de\s*)?(\d+(?:[.,]\d+)?)?\s*([a-zéèêà]*)", seg)
        if not m:
            continue
        n1 = float(m.group(1).replace(",", "."))
        if m.group(3):
            n2 = float(m.group(3).replace(",", "."))
            u = m.group(4) or ""
            valeur, u_finale = n1 * n2, u
            compte += n1
        else:
            valeur, u_finale = n1, m.group(2) or ""
            compte += 1
        if u_finale in UNITES:
            unite = UNITES[u_finale]
        total += valeur if signe == "+" else -valeur
        ok = True
    if not ok:
        return None
    aff = f"{total:g}".replace(".", ",")
    if unite:
        return f"Ça fait {aff} {unite} au total, pour {int(compte)} éléments comptés."
    return f"Ça fait {aff} au total."

def nf(n):
    return f"{n} fichier" + ("s" if n > 1 else "")

def ng(n):
    return f"{n} groupe" + ("s" if n > 1 else "") + " de doublons"

def taille(o):
    if o >= 10**9:
        return f"{o / 10**9:.1f}".replace(".", ",") + " gigaoctets"
    if o >= 10**6:
        return f"{int(o / 10**6)} mégaoctets"
    return "moins d'un mégaoctet"

def _corbeille():
    d = H + "/nova_corbeille"
    os.makedirs(d, exist_ok=True)
    return d

def _deplacer_vers_corbeille(chemin):
    try:
        dest = os.path.join(_corbeille(), os.path.basename(chemin))
        base, ext = os.path.splitext(dest)
        i = 1
        while os.path.exists(dest):
            dest = f"{base}_{i}{ext}"
            i += 1
        shutil.move(chemin, dest)
        return True
    except Exception:
        return False

def _dans_racine(chemin):
    try:
        return os.path.realpath(chemin).startswith(os.path.realpath(RACINE) + os.sep)
    except Exception:
        return False

def supprimer_doublons():
    if not os.path.exists(H + "/nova_doublons.txt"):
        if confirmer("Je n'ai pas encore de liste de doublons. Je lance l'analyse d'abord ?"):
            doublons(demander=False)
        else:
            return
    lignes = [l.strip() for l in open(H + "/nova_doublons.txt") if l.strip()]
    if not lignes:
        parler("Je n'ai trouvé aucun doublon à supprimer.")
        return
    a_supprimer, gagne = [], 0
    for ligne in lignes:
        fichiers = [f for f in ligne.split(" | ") if os.path.isfile(f) and _dans_racine(f)]
        if len(fichiers) < 2:
            continue
        fichiers.sort(key=lambda c: os.path.getmtime(c))
        garde, doubles = fichiers[0], fichiers[1:]
        for d in doubles:
            a_supprimer.append(d)
            gagne += os.path.getsize(d)
    if not a_supprimer:
        parler("Je n'ai rien à supprimer, les fichiers ont peut-être déjà bougé.")
        return
    if not confirmer(f"Je vais déplacer {nf(len(a_supprimer))} en double vers la corbeille, pour libérer {taille(gagne)}. Un exemplaire de chaque est gardé. Je le fais ?"):
        parler("D'accord, je ne touche à rien.")
        return
    ok = sum(1 for c in a_supprimer if _deplacer_vers_corbeille(c))
    parler(f"C'est fait, {nf(ok)} déplacés vers la corbeille. Tape vide corbeille pour les effacer pour de bon.")

def supprimer_lourds(p):
    if not os.path.exists(H + "/nova_lourds.txt"):
        if confirmer("Je n'ai pas encore de liste de fichiers lourds. Je lance la recherche d'abord ?"):
            lourds()
        else:
            return
    lignes = [l.strip() for l in open(H + "/nova_lourds.txt") if l.strip()]
    chemins = []
    for l in lignes:
        if " | " in l:
            chemins.append(l.split(" | ", 1)[1])
    m = re.search(r"\bnumero\s*(\d+)|\bn\s*(\d+)|^\s*(\d+)\s", p)
    if m and chemins:
        idx = int(next(g for g in m.groups() if g)) - 1
        if 0 <= idx < len(chemins):
            c = chemins[idx]
            if not os.path.isfile(c) or not _dans_racine(c):
                parler("Ce fichier n'existe plus ou n'est pas dans un dossier que je gère.")
                return
            if confirmer(f"Je déplace vers la corbeille : {os.path.basename(c)}, {taille(os.path.getsize(c))}. Je le fais ?"):
                parler("C'est fait." if _deplacer_vers_corbeille(c) else "Je n'ai pas réussi à le déplacer.")
            else:
                parler("D'accord, je ne touche à rien.")
            return
    parler(f"Il y a {nf(len(chemins))} fichiers lourds. Dis : supprime le fichier numéro, suivi du chiffre affiché dans nova lourds point t x t.")
    for i, c in enumerate(chemins[:10], 1):
        print(f"{i}. {c}")

def vider_corbeille():
    d = _corbeille()
    fichiers = [os.path.join(d, f) for f in os.listdir(d)] if os.path.isdir(d) else []
    if not fichiers:
        parler("La corbeille est déjà vide.")
        return
    total = sum(os.path.getsize(f) for f in fichiers)
    if not confirmer(f"La corbeille contient {nf(len(fichiers))}, soit {taille(total)}. Je les efface pour de bon, sans retour possible. Je le fais ?"):
        parler("D'accord, je garde la corbeille telle quelle.")
        return
    for f in fichiers:
        try:
            os.remove(f)
        except OSError:
            pass
    parler("Corbeille vidée.")

def _nom_app(paquet):
    if paquet in NOMS_APPS:
        return NOMS_APPS[paquet]
    return paquet.split(".")[-1].capitalize() if "." in paquet else paquet

def scanner_media_apps():
    base = os.path.join(RACINE, "Android", "media")
    res = {}
    if not os.path.isdir(base):
        return res
    try:
        dossiers_app = os.listdir(base)
    except OSError:
        return res
    for paquet in dossiers_app:
        chemin_app = os.path.join(base, paquet)
        if not os.path.isdir(chemin_app):
            continue
        total = 0
        for dossier, sous, liste in os.walk(chemin_app):
            for f in liste:
                try:
                    total += os.path.getsize(os.path.join(dossier, f))
                except OSError:
                    pass
        if total > 0:
            res[paquet] = total
    return res

def espace_applis():
    if not os.path.isdir(RACINE):
        parler("Je n'ai pas accès à tes fichiers.")
        return
    parler("Je regarde ce que tes applications ont laissé dans le stockage partagé, un instant.")
    res = scanner_media_apps()
    if not res:
        parler("Je n'ai rien trouvé d'accessible du côté des applications. C'est peut-être vide, ou caché dans leurs données privées.")
        return
    top = sorted(res.items(), key=lambda x: -x[1])[:5]
    total = sum(res.values())
    nb = len(res)
    parler(f"J'ai trouvé {taille(total)} laissés par {nb} application" + ("s" if nb > 1 else "") + " dans le dossier partagé. Les plus gros : " +
           ", ".join(f"{_nom_app(p)} avec {taille(t)}" for p, t in top) + ".")
    parler("Attention, ceci ne montre que ce qu'elles partagent, pas leurs données privées internes, toujours hors de ma portée sans root.")

parler("Nova est prête.")
verif_limite()
while True:
    p = nettoyer(input("Toi : "))
    if p and not traiter(p):
        break
