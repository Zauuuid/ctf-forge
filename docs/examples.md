# Examples

All examples assume `bash install.sh` has finished and your agent was restarted.

## 1. Category known, files provided

```bash
mkdir -p ~/ctf/picoctf/baby-rsa && cd ~/ctf/picoctf/baby-rsa
# put output.txt and chall.py here, then start your agent
```

```text
/ctf-crypto Files: chall.py, output.txt. The challenge name is baby-rsa. Hint: e is small.
```

## 2. Category unknown

```text
/solve-challenge Unknown category. Files are in this folder. Flag format is HTB{...}.
```

`solve-challenge` triages the files, picks the category and loads the matching skill.

## 3. A challenge URL

```text
/solve-challenge https://ctf.example.com/challenges/12
```

## 4. A remote service

```text
/solve-challenge pwn, binary ./vuln, remote nc ctf.example.com 31337. Hint: look at the menu options.
```

## 5. Quick triage by hand with the bundled scripts

```bash
python3 -m ctf_forge kit list
python3 -m ctf_forge kit run analyze/triage.sh ./challenge.bin
python3 -m ctf_forge kit run crypto/identify-hash.sh 5f4dcc3b5aa765d61d8327deb882cf99
python3 -m ctf_forge kit run stego/stego-pipeline.sh ./image.png
```

Each script prints a JSON summary with suggested next commands.

## 6. Keep memory between sessions

```bash
python3 -m ctf_forge memory init ~/CTFMemory
python3 -m ctf_forge memory recall rsa small exponent        # before a challenge
python3 -m ctf_forge memory log --event picoCTF --name baby-rsa --category crypto \
    --status solved --flag 'picoCTF{...}' --summary 'small e, integer cube root'   # after
```

Open `~/CTFMemory` in Obsidian to browse and link the notes.

## 7. Check what is installed

```bash
python3 -m ctf_forge doctor
python3 -m ctf_forge tools verify
```

## 8. Update later

```bash
python3 -m ctf_forge skills update
```
