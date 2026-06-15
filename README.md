# Gra Oczko (sieciowa)

> **Prosta gra na dwóch graczy** - zadanie na przedmiot **Aplikacje Sieciowe**.  
> Projekt jest w trakcie - README też może się jeszcze zmienić.

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org)  
[![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-green.svg)](https://github.com/TomSchimansky/CustomTkinter)

---

## O projekcie

Gra **Oczko** (zbliżona do blackjacka) dla **dwóch graczy** w sieci LAN.  
Jeden komputer **tworzy grę** (host + serwer TCP), drugi **dołącza** po adresie **IP:PORT**.

- każdy gracz zaczyna z **1000 monet**
- przed rundą: **zakład**
- w rundzie: **Hit** (dobierz) lub **Stay** (zostań) - obaj grają **jednocześnie**
- wynik i monety liczy **serwer** (listen server)

---

## Jak grać

1. Gracz 1: **Create Game** - na ekranie pojawi się adres **IP:PORT** (podaj go drugiej osobie).
2. Gracz 2: **Join Game** - wpisz ten sam format (np. `192.168.1.5:54321`) i **Connect**.
3. Po połączeniu oboje: wpiszcie **zakład** i kliknijcie **Bet**.
4. W rundzie używajcie **Hit** / **Stay**. Przycisk **End Game** wraca do menu.

Gra działa w sieci lokalnej (ten sam Wi-Fi / LAN). Port wybiera system przy starcie hosta.

---

## Technologie

| Element | Opis |
|--------|------|
| Python | logika gry i GUI |
| `socket` | połączenie TCP |
| `threading` | serwer i odbiór wiadomości |
| `json` | protokół klient - serwer |
| `random` | losowanie kart (wartości) |
| CustomTkinter | interfejs graficzny |

---

## Instalacja

### 1. Klonowanie (opcjonalnie)

```bash
git clone <adres-twojego-repozytorium>
cd "Gra Oczko"
```

### 2. Środowisko wirtualne

```bash
python -m venv .venv
```

**Windows**

```bash
.venv\Scripts\activate
```

**Linux / macOS**

```bash
source .venv/bin/activate
```

### 3. Zależności

```bash
pip install -r requirements.txt
```

---

## Uruchomienie

```bash
python main.py
```

### Plik .exe (PyInstaller)

```bash
pip install pyinstaller
python -m PyInstaller --noconfirm GraOczko.spec
```

Gotowa gra jest w folderze `dist/GraOczko/` - uruchamiasz `GraOczko.exe` z tego folderu.

**Wysylka innej osobie:** spakuj caly folder `GraOczko` do ZIP (nie sam exe - obok sa potrzebne biblioteki i tkinter).

> Uwaga: jeden plik `--onefile` czesto wywala blad `_tcl_data` przy CustomTkinter. Dlatego budujemy wersje folderowa - dziala stabilniej.
