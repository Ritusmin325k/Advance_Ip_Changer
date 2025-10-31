#!/bin/bash
# Tor management script for Advance IP Changer

TORRC="$HOME/.torrc"
CONTROL_PORT=9051
SOCKS_PORT=9050
PASS="12345"

start_tor() {
    echo "[*] Starting tor..."
    if pgrep -x tor > /dev/null; then
        echo "[+] Tor already running."
        exit 0
    fi

    if [ ! -f "$TORRC" ]; then
        HASHED_PASS=$(tor --hash-password "$PASS" | tail -n1)
        cat > "$TORRC" <<EOF
SocksPort $SOCKS_PORT
ControlPort $CONTROL_PORT
HashedControlPassword $HASHED_PASS
DataDirectory $HOME/.tor-data
Log notice stdout
EOF
    fi

    tor -f "$TORRC" > /dev/null 2>&1 &
    sleep 5
    echo "[+] Tor started."
}

stop_tor() {
    echo "[*] Stopping tor..."
    pkill -x tor || true
    echo "[+] Tor stopped."
}

newnym() {
    echo "[*] Requesting new identity..."
    printf 'AUTHENTICATE "%s"\r\nSIGNAL NEWNYM\r\nQUIT\r\n' "$PASS" | nc 127.0.0.1 $CONTROL_PORT >/dev/null
}

getip() {
    curl --socks5-hostname 127.0.0.1:9050 -s https://check.torproject.org/api/ip | grep -oE '"IP":"[0-9.]+"' | cut -d'"' -f4
}

status() {
    if pgrep -x tor > /dev/null; then
        echo "[+] Tor is running."
        echo "[*] Current IP: $(bash $0 getip)"
    else
        echo "[-] Tor is not running."
    fi
}

case "$1" in
    start) start_tor ;;
    stop) stop_tor ;;
    newnym) newnym ;;
    getip) getip ;;
    status) status ;;
    *) echo "Usage: $0 {start|stop|newnym|getip|status}" ;;
esac
