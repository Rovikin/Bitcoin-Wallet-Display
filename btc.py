import subprocess
import json
import time
import requests
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

def run_electrum_command(command):
    """Menjalankan perintah Electrum dan menangani output/error."""
    try:
        result = subprocess.run(
            command, shell=True, text=True, capture_output=True
        )
        if result.returncode != 0:
            return f"Error: {result.stderr.strip()}"
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def get_balance_in_btc(balance_data):
    """Mengambil saldo BTC (terkonfirmasi & belum terkonfirmasi) dari JSON Electrum."""
    try:
        balance_data = json.loads(balance_data)
        confirmed = float(balance_data.get("confirmed", 0))
        unconfirmed = float(balance_data.get("unconfirmed", 0))
        return confirmed, unconfirmed
    except (json.JSONDecodeError, ValueError, KeyError):
        return 0.0, 0.0

def get_transaction_history():
    """Mengambil riwayat transaksi dari Electrum."""
    history = run_electrum_command("electrum onchain_history")
    try:
        history_data = json.loads(history)
        transactions = history_data.get("transactions", [])
        return sorted(transactions, key=lambda x: x.get("date", ""), reverse=True)  # Urutkan terbaru di atas
    except (json.JSONDecodeError, ValueError):
        return []

def get_btc_price_idr():
    """Mengambil harga BTC ke IDR dari CoinGecko."""
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "bitcoin", "vs_currencies": "idr"}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Pastikan tidak ada error HTTP
        price_data = response.json()
        return price_data.get("bitcoin", {}).get("idr", 0)
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Error fetching BTC price: {e}[/bold red]")
        return 0

def display_wallet_info(address, confirmed_balance, unconfirmed_balance, btc_price_idr, transactions):
    """Menampilkan informasi wallet dalam tabel Rich."""
    subprocess.run("clear", shell=True)

    table = Table(title="Bitcoin Wallet Info", show_header=True, header_style="bold magenta", show_lines=True)
    table.add_column("Attribute", style="dim", width=20)
    table.add_column("Value", justify="right")

    table.add_row("Unused Address", address)
    table.add_row("Confirmed Balance", f"₿ {confirmed_balance:.8f} (Rp {confirmed_balance * btc_price_idr:,.0f})")
    table.add_row("Unconfirmed Balance", f"₿ {unconfirmed_balance:.8f} (Rp {unconfirmed_balance * btc_price_idr:,.0f})")

    if transactions:
        table.add_row("", "")
        table.add_row("[bold]Last Transactions[/bold]", "")
        for tx in transactions:
            txid = tx.get("txid", "Unknown")
            amount = float(tx.get("bc_value", 0))
            date = tx.get("date", "Unknown")
            direction = "Incoming" if tx.get("incoming", False) else "Outgoing"
            table.add_row(
                f"{direction} TX",
                f"₿ {amount:.8f} ({date})\n[dim]{txid}[/dim]"
            )
    else:
        table.add_row("[bold red]No transaction history found.[/bold red]", "")

    console.print(table)

def main():
    """Fungsi utama untuk menampilkan informasi wallet."""
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task("[cyan]Starting Electrum daemon...", total=None)
        subprocess.run("electrum daemon -d", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)

    console.print("[bold yellow]Electrum is requesting your password...[/bold yellow]")  
    run_electrum_command("electrum load_wallet")  
    console.print("[green]Wallet loaded successfully![/green]")  

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task("[cyan]Fetching unused address...", total=None)
        address = run_electrum_command("electrum getunusedaddress")
        time.sleep(1)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task("[cyan]Fetching balance...", total=None)
        balance = run_electrum_command("electrum getbalance")
        confirmed_balance, unconfirmed_balance = get_balance_in_btc(balance)
        time.sleep(1)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task("[cyan]Fetching BTC price in IDR...", total=None)
        btc_price_idr = get_btc_price_idr()
        time.sleep(1)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task("[cyan]Fetching transaction history...", total=None)
        transactions = get_transaction_history()
        time.sleep(1)

    display_wallet_info(address, confirmed_balance, unconfirmed_balance, btc_price_idr, transactions)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        progress.add_task("[cyan]Stopping Electrum daemon...", total=None)
        subprocess.run("electrum stop", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)

if __name__ == "__main__":
    main()
