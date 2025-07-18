# Sistem de Curățenie pentru InfoPaste

## Descriere

Sistemul de curățenie automată pentru paste-urile expirate din InfoPaste.

## Funcționalități

### 1. Curățenie Automată
- **Când se rulează**: La fiecare 10 creări de paste
- **Ce face**: Șterge paste-urile expirate și datele asociate
- **Avantaj**: Nu necesită configurare externă

### 2. Curățenie Manuală
- **Endpoint**: `/admin/cleanup_expired_pastes`
- **Acces**: Doar pentru utilizatori autentificați
- **Utilizare**: Pentru curățenie manuală când este necesar

### 3. Script Extern
- **Fișier**: `cleanup_pastes.py`
- **Utilizare**: Pentru cron jobs sau rulare manuală
- **Avantaj**: Poate fi programat independent de aplicație

## Ce se șterge

Când un paste expiră, se șterg:
- ✅ Paste-ul principal
- ✅ Înregistrările de vizualizări
- ✅ Comentariile
- ✅ Explicațiile AI
- ✅ Aprecierile

## Configurare pentru Scaling

### Pentru producție (recomandat):

1. **Cron Job** (Linux/Mac):
```bash
# Rulează curățenia la fiecare 6 ore
0 */6 * * * /path/to/python /path/to/cleanup_pastes.py >> /var/log/paste_cleanup.log 2>&1
```

2. **Windows Task Scheduler**:
```cmd
# Creează un task care rulează cleanup_pastes.py la fiecare 6 ore
schtasks /create /tn "PasteCleanup" /tr "python C:\path\to\cleanup_pastes.py" /sc daily /mo 1 /st 00:00
```

3. **Docker/Container**:
```dockerfile
# Adaugă în Dockerfile
COPY cleanup_pastes.py /app/
RUN chmod +x /app/cleanup_pastes.py

# În docker-compose.yml
services:
  cleanup:
    build: .
    command: ["python", "/app/cleanup_pastes.py"]
    volumes:
      - ./infopaste.db:/app/infopaste.db
    restart: unless-stopped
```

### Pentru dezvoltare:

Curățenia se rulează automat la fiecare 10 creări de paste, deci nu este necesară configurare suplimentară.

## Monitorizare

### Logs
- Scriptul extern generează logs cu timestamp
- Poți redirecționa output-ul către un fișier de log

### Endpoint de verificare
```bash
curl http://localhost:5000/admin/cleanup_expired_pastes
```

## Optimizări pentru Scaling

### Pentru volume mari:
1. **Indexuri** pe `expires_at`:
```sql
CREATE INDEX IF NOT EXISTS idx_expires_at ON code_pastes(expires_at);
```

2. **Batch processing** pentru paste-uri foarte multe:
```python
# În loc să ștergi toate odată, șterge în batch-uri
BATCH_SIZE = 1000
```

3. **Monitoring**:
- Adaugă metrici pentru numărul de paste-uri șterse
- Monitorizează timpul de execuție
- Alerte pentru erori

## Backup înainte de curățenie

Recomandarea este să faci backup la baza de date înainte de a activa curățenia automată:

```bash
cp infopaste.db infopaste.db.backup.$(date +%Y%m%d)
```

## Troubleshooting

### Probleme comune:
1. **Permisiuni**: Asigură-te că scriptul are permisiuni de scriere
2. **Lock-uri**: Verifică că aplicația nu blochează baza de date
3. **Disk space**: Monitorizează spațiul liber pe disk

### Debug:
```bash
python cleanup_pastes.py --verbose
``` 