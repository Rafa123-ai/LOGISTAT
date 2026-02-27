# Ir a la carpeta del proyecto
Set-Location "C:\MIS DOCUMENTOS\Programa Logistica V5\21-02-26 logistat2\LOGISTAT_BACKUP"

# Liberar puerto 8501 si está ocupado
$port=8501
$line = netstat -ano | Select-String ":$port\s+.*LISTENING\s+(\d+)$"
if($line){
    $pid=$line.Matches[0].Groups[1].Value
    Stop-Process -Id $pid -Force
}

# Abrir navegador
Start-Process "http://localhost:8501"

# Ejecutar Streamlit en puerto fijo
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
