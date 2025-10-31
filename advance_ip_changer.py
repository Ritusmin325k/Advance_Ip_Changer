#!/usr/bin/env python3
import os
import time
import requests
import subprocess
import socket
import sys
from rich.console import Console
from rich.panel import Panel
from banner import banner
# --- Dependency Check ---
# This is CRITICAL to prevent the IP leak you saw.
try:
    from stem import Signal
    from stem.control import Controller
    import socks  # This module is installed by 'requests[socks]'
except ImportError as e:
    print(f"\n[ERROR] Missing critical dependencies: {e.name}")
    print("Your original script was leaking your real IP because a library was missing.")
    print("\nPlease install all requirements by running:")
    print("\npip install stem 'requests[socks]' rich\n")
    sys.exit(1)

# --- Configuration ---
console = Console()
# We'll store our Tor data in a dedicated directory in your home folder
TOR_DIR = os.path.expandvars("$HOME/.my_ip_changer_tor")
TORRC_PATH = os.path.join(TOR_DIR, "torrc")
DATA_DIR = os.path.join(TOR_DIR, "data")
CONTROL_PORT = 9051
SOCKS_PORT = 9050
# Never use '12345'. Use a strong, unique password.
PASSWORD = "change_this_to_a_strong_password!"

banner()
def is_tor_running() -> bool:
    """Checks if a 'tor' process is currently running using pgrep."""
    result = subprocess.run(["pgrep", "-x", "tor"], capture_output=True)
    return result.returncode == 0

def wait_for_port(port: int, host: str = '127.0.0.1', timeout: int = 30) -> bool:
    """
    Waits for a network port to become open.
    This is much more reliable than time.sleep().
    """
    console.print(f"[yellow]* Waiting for Tor Control Port ({port}) to open...[/yellow]", end="")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Try to create a connection to the port
            with socket.create_connection((host, port), timeout=1):
                console.print("\n[green]✓ Port is open![/green]")
                return True
        except (socket.timeout, ConnectionRefusedError):
            # Port is not open yet
            # NEW, FIXED LINES
            console.print(".", end="")
            sys.stdout.flush()
            time.sleep(1)
    console.print("\n[red]✗ Timed out waiting for Tor port.[/red]")
    return False

def start_tor():
    """
    Starts the Tor service using our custom configuration.
    This function replaces the "stuck at 100%" bug.
    """
    if is_tor_running():
        console.print("[green]✓ Tor is already running.[/green]")
        return

    console.print("[yellow]* Starting Tor...[/yellow]")
    
    # Ensure our config directories exist
    os.makedirs(TOR_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)

    # Create torrc file if it doesn't exist
    if not os.path.exists(TORRC_PATH):
        console.print(f"[yellow]* No torrc found. Creating one at {TORRC_PATH}[/yellow]")
        try:
            # Get hashed password from Tor
            result = subprocess.run(
                ["tor", "--hash-password", PASSWORD],
                capture_output=True, text=True, check=True, encoding='utf-8'
            )
            hashed_pass = result.stdout.strip().splitlines()[-1]
            
            torrc_content = f"""
SocksPort {SOCKS_PORT}
ControlPort {CONTROL_PORT}
HashedControlPassword {hashed_pass}
DataDirectory {DATA_DIR}
Log notice stdout
CookieAuthentication 0
"""
            with open(TORRC_PATH, "w") as f:
                f.write(torrc_content)
            console.print("[green]✓ Created new torrc file.[/green]")
        
        except FileNotFoundError:
            console.print("[red]✗ Error: 'tor' command not found. Is Tor installed on your system?[/red]")
            return
        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗ Error hashing password: {e.stderr}[/red]")
            return

    # Start Tor as a background (daemon) process
    # This is the correct way to start it without it "getting stuck"
    try:
        subprocess.Popen(
            ["tor", "-f", TORRC_PATH],
            stdout=subprocess.DEVNULL, # Send bootstrap output to null
            stderr=subprocess.DEVNULL
        )
        
        # Wait for the control port to be active instead of a blind sleep
        if wait_for_port(CONTROL_PORT):
            console.print("[green]✓ Tor started successfully.[/green]")
        else:
            console.print("[red]✗ Tor process started but Control Port is not responding.[/red]")
            
    except FileNotFoundError:
        console.print("[red]✗ Error: 'tor' command not found. Is Tor installed?[/red]")
    except Exception as e:
        console.print(f"[red]✗ An error occurred while starting Tor: {e}[/red]")

def stop_tor():
    """Stops any running 'tor' process."""
    console.print("[yellow]* Stopping Tor...[/yellow]")
    if not is_tor_running():
        console.print("[grey]✓ Tor was not running.[/grey]")
        return
        
    # Use pkill to stop the process by name
    subprocess.run(["pkill", "-x", "tor"], capture_output=True)
    
    time.sleep(1) # Give it a second to shut down
    if not is_tor_running():
        console.print("[red]✗ Tor stopped.[/red]")
    else:
        console.print("[yellow]! Tor process may still be running. (pkill failed)[/yellow]")

def get_ip() -> str | None:
    """
    Fetches the current external IP through the Tor SOCKS proxy.
    This now correctly uses the socks5h protocol.
    """
    proxies = {
        "http": f"socks5h://127.0.0.1:{SOCKS_PORT}",
        "https": f"socks5h://127.0.0.1:{SOCKS_PORT}",
    }
    try:
        r = requests.get("https://api.ipify.org?format=text", proxies=proxies, timeout=15)
        r.raise_for_status() # Raise an error for bad status codes (e.g., 404, 500)
        return r.text.strip()
    except requests.exceptions.RequestException as e:
        console.print(f"\n[red]✗ Error fetching IP: {e}[/red]")
        console.print("[yellow]! This can happen if Tor is bootstrapping or the connection failed.[/yellow]")
        return None
    except Exception as e:
        console.print(f"\n[red]✗ An unexpected error occurred during IP fetch: {e}[/red]")
        return None

def change_ip():
    """Signals Tor to request a new circuit (new IP)."""
    try:
        with Controller.from_port(port=CONTROL_PORT) as controller:
            # We must authenticate with the password we set in the torrc
            controller.authenticate(password=PASSWORD)
            controller.signal(Signal.NEWNYM)
            console.print("[green]✓ NEWNYM signal sent.[/green]")
            return True
    except Exception as e:
        console.print(f"[red]✗ Error connecting to Tor Controller: {e}[/red]")
        console.print(f"[yellow]! Is Tor running and configured for ControlPort {CONTROL_PORT}?[/yellow]")
        return False

def start_ip_changing():
    """
    Main loop for changing IP address periodically.
    This now checks if Tor is running first.
    """
    
    # --- This is the fix for your "error when tor is not started" bug ---
    if not is_tor_running():
        console.print("[red]✗ Tor is not running. Please start Tor (option 1) first.[/red]")
        return

    try:
        total = int(console.input("[cyan]How many times to change IP? [/cyan]"))
        delay = int(console.input("[cyan]Seconds between changes? (e.g., 10) [/cyan]"))
    except ValueError:
        console.print("[red]✗ Invalid input. Please enter numbers.[/red]")
        return

    console.print(f"[yellow]Starting IP change cycle ({total} times)...[/yellow]")
    for i in range(total):
        console.print(Panel(f"Cycle {i+1}/{total}", style="blue"))
        console.print(f"[yellow]* Requesting new IP...[/yellow]")
        
        if not change_ip():
            console.print("[red]✗ Failed to send NEWNYM signal. Aborting loop.[/red]")
            break
            
        console.print("[yellow]* Waiting for new circuit to build...[/yellow]")
        time.sleep(5) # Give Tor time to establish a new path
        
        ip = get_ip()
        if ip:
            console.print(f"[green]✓ New IP:[/green] [bold]{ip}[/bold]")
        else:
            console.print("[red]✗ Failed to fetch new IP.[/red]")
        
        if i < total - 1:
            console.print(f"[grey]Waiting for {delay} seconds...[/grey]")
            time.sleep(delay)
    
    console.print("[green]✓ IP changing cycle finished.[/green]")

def status():
    """Checks and reports the status of Tor and the current IP."""
    if is_tor_running():
        console.print("[green]✓ Tor is running.[/green]")
        console.print("[yellow]* Fetching current Tor IP...[/yellow]")
        ip = get_ip()
        if ip:
            console.print(f"[white]Current Tor IP: [bold]{ip}[/bold][/white]")
        else:
            console.print("[red]✗ Could not fetch Tor IP.[/red]")
    else:
        console.print("[red]✗ Tor is not running.[/red]")

def main():
    """Main menu loop."""
    banner()
    while True:
        console.print("\n[yellow]1)[/yellow] Start Tor\n[yellow]2)[/yellow] Stop Tor\n[yellow]3)[/yellow] Start IP Changing\n[yellow]4)[/yellow] Status\n[yellow]5)[/yellow] Exit")
        choice = console.input("\n[bold cyan]Select option:[/bold cyan] ").strip()
        
        if choice == "1":
            start_tor()
        elif choice == "2":
            stop_tor()
        elif choice == "3":
            start_ip_changing()
        elif choice == "4":
            status()
        elif choice == "5":
            stop_tor()
            console.print("[bold]Goodbye![/bold]")
            break
        else:
            console.print("[red]Invalid choice[/red]")

if __name__ == "__main__":
      banner()
      main()
