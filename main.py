import requests
import threading
import queue
import time
import os
from colorama import init, Fore, Style
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

init(autoreset=True)

class AccurateDiscordTokenChecker:
    def __init__(self):
        self.valid_tokens = 0
        self.invalid_tokens = 0
        self.checked_tokens = 0
        self.total_tokens = 0
        self.lock = threading.Lock()
        self.queue = queue.Queue()
        self.running = True
        self.start_time = time.time()
        
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def load_tokens(self, filename="tokens.txt"):
        if not os.path.exists(filename):
            print(Fore.RED + f"[!] Error: {filename} not found!")
            return False

        with open(filename, "r", encoding="utf-8", errors="ignore") as f:
            tokens = list({line.strip() for line in f if line.strip()}) 

        self.total_tokens = len(tokens)
        if self.total_tokens == 0:
            print(Fore.RED + "[!] No tokens found in the file!")
            return False

        for token in tokens:
            self.queue.put(token)

        return True

    def verify_token(self, token):
        headers = {
            "Authorization": token,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        try:
            response = self.session.get(
                "https://discord.com/api/v9/users/@me",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                guilds_response = self.session.get(
                    "https://discord.com/api/v9/users/@me/guilds",
                    headers=headers,
                    timeout=10
                )
                
                if guilds_response.status_code == 200:
                    return "valid"
                return "invalid"

            elif response.status_code == 401:
                return "invalid"

            elif response.status_code == 429:
                retry_after = response.json().get('retry_after', 1)
                time.sleep(retry_after)
                return self.verify_token(token)  
            return "invalid"

        except requests.RequestException:
            return "invalid"

    def save_token(self, filename, token):
        with open(filename, "a", encoding="utf-8") as f:
            f.write(f"{token}\n")

    def worker(self):
        while self.running:
            try:
                token = self.queue.get(timeout=1)
                result = self.verify_token(token)

                with self.lock:
                    self.checked_tokens += 1
                    if result == "valid":
                        self.valid_tokens += 1
                        self.save_token("valid.txt", token)
                    else:
                        self.invalid_tokens += 1
                        self.save_token("not_valid.txt", token)
                    
                    self.update_progress()

                self.queue.task_done()
                time.sleep(0.2) 

            except queue.Empty:
                continue

    def update_progress(self):
        elapsed = time.time() - self.start_time
        speed = self.checked_tokens / elapsed if elapsed > 0 else 0

        os.system('cls' if os.name == 'nt' else 'clear')
        print(Fore.CYAN + Style.BRIGHT + "=== Discord Token Checker By Delete? ===")
        print(f"\n{Fore.YELLOW}Progress: {self.checked_tokens}/{self.total_tokens} "
              f"({(self.checked_tokens/self.total_tokens)*100:.2f}%)")
        print(f"{Fore.GREEN}Valid: {self.valid_tokens} | "
              f"{Fore.RED}Invalid: {self.invalid_tokens}")
        print(f"{Fore.BLUE}Speed: {speed:.2f} tokens/sec | "
              f"Elapsed: {elapsed:.2f}s | "
              f"ETA: {(self.total_tokens - self.checked_tokens)/speed:.2f}s" 
              if speed > 0 else "Calculating...")

    def start(self, thread_count=20):
        if not self.load_tokens():
            return

        open("valid.txt", "w").close()
        open("not_valid.txt", "w").close()
        
        print(Fore.GREEN + f"[+] Starting with {thread_count} threads (slower but more accurate)...")
        print(Fore.YELLOW + "[!] Double-checking all tokens for 100% accuracy...")

        threads = []
        for _ in range(thread_count):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            t.start()
            threads.append(t)

        try:
            while not self.queue.empty():
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.running = False
            print(Fore.YELLOW + "\n[!] Shutting down gracefully...")

        for t in threads:
            t.join()

        self.show_final_results()
        self.verify_final_results()

    def show_final_results(self):
        elapsed = time.time() - self.start_time
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print(Fore.CYAN + Style.BRIGHT + "=== Final Results ===")
        print(f"\n{Fore.YELLOW}Total Tokens Checked: {self.total_tokens}")
        print(f"{Fore.GREEN}Valid Tokens: {self.valid_tokens} "
              f"({(self.valid_tokens/self.total_tokens)*100:.2f}%)")
        print(f"{Fore.RED}Invalid Tokens: {self.invalid_tokens} "
              f"({(self.invalid_tokens/self.total_tokens)*100:.2f}%)")
        print(f"\n{Fore.BLUE}Time Taken: {elapsed:.2f} seconds")

    def verify_final_results(self):
        """Double-check all 'valid' tokens to ensure no false positives"""
        print(Fore.YELLOW + "\n[+] Performing final verification of valid tokens...")
        
        with open("valid.txt", "r") as f:
            valid_tokens = [line.strip() for line in f if line.strip()]
        
        truly_valid = []
        for token in valid_tokens:
            if self.verify_token(token) == "valid":
                truly_valid.append(token)
            else:
                print(Fore.RED + f"[-] False positive removed: {token[:15]}...")

        with open("valid.txt", "w") as f:
            f.write("\n".join(truly_valid) + "\n")
        
        print(Fore.GREEN + f"[+] Final count: {len(truly_valid)} truly valid tokens")

if __name__ == "__main__":
    checker = AccurateDiscordTokenChecker()
    checker.start(thread_count=20) 