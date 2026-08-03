# tests/ — 231 tests pytest (1 fichier par module + `test_check_bias.py` pour `scripts/`)

```powershell
& C:\Users\jofar\venvs\arit\Scripts\python.exe -m pytest -q   # attendu : 231 passed
```

`conftest.py` = générateur de bougies synthétiques SEEDÉ (mêmes données à chaque run).
`test_<module>.py` ↔ le module du même nom (voir [`../guide.md`](../guide.md) §3).
