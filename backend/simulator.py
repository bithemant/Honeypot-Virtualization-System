import os
import json
import datetime
import time

# CTF Configuration
FLAGS = {
    '/home/user/user.txt': {'points': 10, 'content': 'FLAG{USER_ACCESS_GRANTED}', 'difficulty': 'Easy'},
    '/root/root.txt': {'points': 50, 'content': 'FLAG{ROOT_PRIVILEGE_ESCALATION}', 'difficulty': 'Hard'},
    '/var/log/secret.log': {'points': 30, 'content': 'FLAG{LOGS_ARE_IMPORTANT}', 'difficulty': 'Medium'},
    '/etc/shadow.bak': {'points': 100, 'content': 'FLAG{ALWAYS_CHECK_BACKUPS}', 'difficulty': 'Expert'},
    '/home/user/.bash_history': {'points': 15, 'content': 'FLAG{HISTORY_REVEALS_SECRETS}', 'difficulty': 'Easy'},
    '/var/www/html/.htaccess': {'points': 25, 'content': 'FLAG{HIDDEN_WEB_CONFIG}', 'difficulty': 'Medium'},
    '/tmp/.cache_key': {'points': 40, 'content': 'FLAG{TEMP_FILES_MATTER}', 'difficulty': 'Medium'},
    '/etc/cron.d/.backdoor': {'points': 60, 'content': 'FLAG{PERSISTENCE_MECHANISM}', 'difficulty': 'Hard'},
    '/home/user/documents/.classified': {'points': 35, 'content': 'FLAG{HIDDEN_IN_PLAIN_SIGHT}', 'difficulty': 'Medium'},
    '/root/.ssh/id_rsa': {'points': 75, 'content': 'FLAG{SSH_KEY_COMPROMISED}', 'difficulty': 'Hard'},
}
MAX_SCORE = sum(f['points'] for f in FLAGS.values())

class VirtualShell:
    def __init__(self):
        self.cwd = "/home/user"
        self.current_user = "user" # Changed from current_user to user
        self.hostname = "ubuntu-server"
        # Simple in-memory file system structure
        # Directories are dicts, files are strings
        self.fs = {
            '/': {
                'home': {
                    'user': {
                        'user.txt': 'FLAG{USER_ACCESS_GRANTED}',
                        '.bash_history': 'FLAG{HISTORY_REVEALS_SECRETS}',
                        'documents': {
                            '.classified': 'FLAG{HIDDEN_IN_PLAIN_SIGHT}',
                            'readme.md': '# Project Notes\nNothing interesting here.'
                        },
                        'downloads': {}
                    }
                },
                'etc': {
                    'passwd': 'root:x:0:0:root:/root:/bin/bash\nuser:x:1000:1000:user:/home/user:/bin/bash',
                    'shadow.bak': 'FLAG{ALWAYS_CHECK_BACKUPS}',
                    'hostname': 'ubuntu-server',
                    'cron.d': {
                        'daily': '0 3 * * * /usr/sbin/logrotate',
                        '.backdoor': 'FLAG{PERSISTENCE_MECHANISM}'
                    }
                },
                'var': {
                    'log': {
                        'syslog': 'Feb 20 10:00:01 ubuntu-server systemd[1]: Started System Logging Service.',
                        'auth.log': 'Feb 20 10:05:22 ubuntu-server sshd[1234]: Accepted password for user from 192.168.1.50 port 54321 ssh2',
                        'secret.log': 'FLAG{LOGS_ARE_IMPORTANT}'
                    },
                    'www': {
                        'html': {
                            'index.html': '<html><body><h1>It Works!</h1></body></html>',
                            '.htaccess': 'FLAG{HIDDEN_WEB_CONFIG}'
                        }
                    }
                },
                'root': {
                    'root.txt': 'FLAG{ROOT_PRIVILEGE_ESCALATION}',
                    '.ssh': {
                        'authorized_keys': 'ssh-rsa AAAAB3NzaC1yc2E...',
                        'id_rsa': 'FLAG{SSH_KEY_COMPROMISED}'
                    }
                },
                'tmp': {
                    '.cache_key': 'FLAG{TEMP_FILES_MATTER}',
                    'session_3a2f.tmp': 'session data...'
                }
            }
        }
        self.history = []
        self.last_flag_found = None
        self.start_time = datetime.datetime.now()
        self.score = 0
        self.found_flags = set()

    def get_prompt(self):
        # Colored prompt: green user@host, blue path
        return f"\x1b[1;32m{self.current_user}@{self.hostname}\x1b[0m:\x1b[1;34m{self.cwd}\x1b[0m$ "

    def resolve_path(self, path):
        # Handle absolute paths
        if path.startswith("/"):
            parts = path.strip("/").split("/")
        else:
            # Handle relative paths
            if self.cwd == "/":
                current_parts = []
            else:
                current_parts = self.cwd.strip("/").split("/")
            
            parts = current_parts + path.split("/")

        # Normalize path
        normalized = []
        for part in parts:
            if part == "" or part == ".":
                continue
            if part == "..":
                if normalized:
                    normalized.pop()
            else:
                normalized.append(part)
        
        return normalized

    def get_node(self, path_parts):
        current = self.fs["/"]
        for part in path_parts:
            if part in current and isinstance(current[part], dict):
                current = current[part]
            else:
                return None
        return current

    def execute_command(self, command_line):
        if not command_line.strip():
            return ""

        parts = command_line.split()
        cmd = parts[0]
        args = parts[1:]
        
        self.history.append(command_line)

        if cmd == "ls":
            return self._cmd_ls(args)
        elif cmd == "cd":
            return self._cmd_cd(args)
        elif cmd == "pwd":
            return self.cwd
        elif cmd == "cat":
            return self._cmd_cat(args)
        elif cmd == "echo":
            return self._cmd_echo(args)
        elif cmd == "mkdir":
            return self._cmd_mkdir(args)
        elif cmd == "sudo":
            return self._cmd_sudo(args)
        elif cmd == "rm":
            return self._cmd_rm(args)
        elif cmd == "touch":
            return self._cmd_touch(args)
        elif cmd == "clear":
            return "__CLEAR__"
        elif cmd == "exit":
            return "__EXIT__"
        elif cmd == "whoami":
            return self.current_user
        elif cmd == "scan":
            return self._cmd_scan(args)
        elif cmd == "trace":
            return self._cmd_trace(args)
        elif cmd == "decrypt":
            return self._cmd_decrypt(args)
        elif cmd == "msg":
            return self._cmd_msg(args)
        elif cmd == "id":
            return f"uid=1000({self.current_user}) gid=1000({self.current_user}) groups=1000({self.current_user}),4(adm),24(cdrom),27(sudo),30(dip)"
        elif cmd == "uname":
            flag = args[0] if args else ""
            if flag == "-a":
                return "Linux ubuntu-server 5.15.0-60-generic #66-Ubuntu SMP Fri Jan 20 14:29:49 UTC 2023 x86_64 GNU/Linux"
            return "Linux"
        elif cmd == "hostname":
            return self.hostname
        elif cmd == "date":
            return datetime.datetime.now().strftime("%a %b %d %H:%M:%S UTC %Y")
        elif cmd == "uptime":
            elapsed = (datetime.datetime.now() - self.start_time).total_seconds()
            mins = int(elapsed // 60)
            return f" {datetime.datetime.now().strftime('%H:%M:%S')} up {mins} min,  1 user,  load average: 0.08, 0.03, 0.01"
        elif cmd == "history":
            return self._cmd_history(args)
        elif cmd == "ifconfig":
            return self._cmd_ifconfig(args)
        elif cmd == "ip":
            return self._cmd_ifconfig(args)
        elif cmd == "netstat":
            return self._cmd_netstat(args)
        elif cmd == "ps":
            return self._cmd_ps(args)
        elif cmd == "w" or cmd == "who":
            return f"{self.current_user}  pts/0  {datetime.datetime.now().strftime('%H:%M')}   0.00s  0.00s  -bash"
        elif cmd == "submit":
            return self._cmd_submit(args)
        elif cmd == "score":
            return self._cmd_score(args)
        elif cmd == "help":
            return "\x1b[1;33mAvailable commands:\x1b[0m ls, cd, pwd, cat, echo, mkdir, rm, touch, sudo, clear, exit,\n               whoami, id, uname, hostname, date, uptime, history, ifconfig, netstat, ps,\n               scan, trace, decrypt, msg, submit, score, w, who, help"
        else:
            return f"\x1b[31m{cmd}: command not found\x1b[0m"

    def _cmd_scan(self, args):
        import random
        target = args[0] if args else "192.168.1.1"
        
        output = [f"Starting Nmap 7.92 ( https://nmap.org ) at {time.strftime('%Y-%m-%d %H:%M %Z')}"]
        output.append(f"Nmap scan report for {target}")
        output.append(f"Host is up ({random.uniform(0.001, 0.05):.4f}s latency).")
        output.append("Not shown: 997 closed tcp ports (reset)")
        output.append("PORT     STATE SERVICE")
        
        ports = [
            ("21/tcp", "open", "ftp"),
            ("22/tcp", "open", "ssh"),
            ("80/tcp", "open", "http"),
            ("443/tcp", "open", "https"),
            ("3306/tcp", "open", "mysql"),
            ("8080/tcp", "open", "http-proxy")
        ]
        
        # Pick random ports to show as open
        selected_ports = sorted(random.sample(ports, k=random.randint(2, 5)))
        for p, s, n in selected_ports:
            output.append(f"{p}  {s}  {n}")
            
        output.append(f"\nNmap done: 1 IP address (1 host up) scanned in {random.uniform(1.2, 5.0):.2f} seconds")
        return "\n".join(output)

    def _cmd_trace(self, args):
        import random
        target = args[0] if args else "target-server.com"
        
        output = [f"traceroute to {target} (10.0.0.5), 30 hops max, 60 byte packets"]
        hops = [
            "192.168.1.1 (192.168.1.1)",
            "10.50.23.1 (10.50.23.1)",
            "isp-backbone.net (203.0.113.5)",
            "core-router.net (198.51.100.12)",
            "nsa-node-7.gov (192.0.2.77)", # Joke hop
            f"{target} (10.0.0.5)"
        ]
        
        for i, hop in enumerate(hops, 1):
            t1 = f"{random.uniform(1, 50):.3f} ms"
            t2 = f"{random.uniform(1, 50):.3f} ms"
            t3 = f"{random.uniform(1, 50):.3f} ms"
            output.append(f" {i}  {hop}  {t1}  {t2}  {t3}")
            
        return "\n".join(output)

    def _cmd_decrypt(self, args):
        # Initial 'decrypting' message, the frontend will just show this text.
        # To make it cool, we could use ANSI colors.
        return "\x1b[32m[+] Initiating Decryption Sequence...\n[+] Brute-forcing cipher...\n[+] Key Found: 0xDEADBEEF\n[+] Payload Decrypted Successfully.\x1b[0m"

    def _cmd_sudo(self, args):
        if not args:
            return "usage: sudo command"
        # Simulate password prompt interactively? 
        # For simplicity, just allow it and say "Access Granted" or execute command as root
        # But we are already root in this sim usually.
        # Let's just execute the command.
        return self.execute_command(" ".join(args))

    def _cmd_rm(self, args):
        # Very basic rm
        if not args:
            return "rm: missing operand"
        target = args[0]
        path_parts = self.resolve_path(target)
        name = path_parts[-1]
        parent_parts = path_parts[:-1]
        parent_node = self.get_node(parent_parts)
        
        if parent_node and name in parent_node:
            del parent_node[name]
            return ""
        return f"rm: cannot remove '{target}': No such file or directory"

    def _cmd_touch(self, args):
        if not args:
            return "touch: missing file operand"
        target = args[0]
        path_parts = self.resolve_path(target)
        name = path_parts[-1]
        parent_parts = path_parts[:-1]
        parent_node = self.get_node(parent_parts)

        if parent_node is not None:
            if name not in parent_node:
                parent_node[name] = "" # Empty file
            return ""
        return f"touch: cannot touch '{target}': No such file or directory"

    def _cmd_ls(self, args):
        target_dir = self.cwd
        show_long = False
        show_all = False
        for a in args:
            if a.startswith('-'):
                if 'l' in a:
                    show_long = True
                if 'a' in a:
                    show_all = True
            else:
                target_dir = a

        path_parts = self.resolve_path(target_dir)
        node = self.get_node(path_parts)

        if node is None:
            return f"\x1b[31mls: cannot access '{target_dir}': No such file or directory\x1b[0m"
        
        if isinstance(node, dict):
            items = []
            for name, content in node.items():
                # Skip hidden files unless -a
                if name.startswith('.') and not show_all:
                    continue
                if isinstance(content, dict):
                    items.append(f"\x1b[1;34m{name}/\x1b[0m")
                elif name.endswith('.txt') or name.endswith('.log') or name.endswith('.bak'):
                    items.append(f"\x1b[1;32m{name}\x1b[0m")
                else:
                    items.append(f"\x1b[37m{name}\x1b[0m")
            
            if show_long:
                lines = []
                for name, content in node.items():
                    if name.startswith('.') and not show_all:
                        continue
                    if isinstance(content, dict):
                        lines.append(f"drwxr-xr-x  2 {self.current_user} {self.current_user}  4096 Feb 20 10:00 \x1b[1;34m{name}/\x1b[0m")
                    else:
                        size = len(str(content))
                        lines.append(f"-rw-r--r--  1 {self.current_user} {self.current_user}  {size:4d} Feb 20 10:00 \x1b[37m{name}\x1b[0m")
                return f"total {len(lines)}\n" + "\n".join(lines)
            
            return "  ".join(items) if items else ""
        else:
            return target_dir

    def _cmd_cd(self, args):
        if not args:
            return "" # do nothing (or go to home, but keeping simple)
        
        target = args[0]
        path_parts = self.resolve_path(target)
        node = self.get_node(path_parts)

        if node is None:
            return f"bash: cd: {target}: No such file or directory"
        
        if not isinstance(node, dict):
            return f"bash: cd: {target}: Not a directory"

        self.cwd = "/" + "/".join(path_parts)
        if len(path_parts) == 0:
            self.cwd = "/"
        return ""

    def _cmd_cat(self, args):
        if not args:
            return ""
        
        target = args[0]
        path_parts = self.resolve_path(target)
        
        # Traverse to parent of file
        filename = path_parts[-1]
        parent_parts = path_parts[:-1]
        parent_node = self.get_node(parent_parts)

        if parent_node is None or filename not in parent_node:
             return f"cat: {target}: No such file or directory"
        
        node = parent_node[filename]
        
        if isinstance(node, dict):
             return f"cat: {target}: Is a directory"
        
        return node

    def _cmd_mkdir(self, args):
        if not args:
            return "mkdir: missing operand"
            
        target = args[0]
        path_parts = self.resolve_path(target)
        
        new_dir_name = path_parts[-1]
        parent_parts = path_parts[:-1]
        parent_node = self.get_node(parent_parts)
        
        if parent_node is None:
             return f"mkdir: cannot create directory '{target}': No such file or directory"
             
        if new_dir_name in parent_node:
             return f"mkdir: cannot create directory '{target}': File exists"
             
        parent_node[new_dir_name] = {}
        return ""

    def _cmd_echo(self, args):
        return " ".join(args)

    def _cmd_msg(self, args):
        if not args:
            return "\x1b[33mUsage: msg <message to admin>\x1b[0m"
        message = " ".join(args)
        return f"__MSG__{message}"

    def _cmd_submit(self, args):
        if not args:
            return "\x1b[33mUsage: submit <FLAG{...}>\x1b[0m\n\x1b[90mExample: submit FLAG{USER_ACCESS_GRANTED}\x1b[0m"
        flag_text = args[0]
        # Check if this flag matches any known flag
        for path, info in FLAGS.items():
            if info['content'] == flag_text:
                if path in self.found_flags:
                    return f"\x1b[33m[!] Flag already submitted: {flag_text}\x1b[0m"
                # Mark as found
                self.found_flags.add(path)
                self.score += info['points']
                self.last_flag_found = {
                    'path': path,
                    'points': info['points'],
                    'total_score': self.score
                }
                return f"__SUBMIT__{flag_text}"
        return f"\x1b[31m[✗] Invalid flag: {flag_text}\x1b[0m"

    def _cmd_score(self, args):
        elapsed = (datetime.datetime.now() - self.start_time).total_seconds()
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        lines = [
            "\x1b[1;33m╔══════════════════════════════════════╗\x1b[0m",
            "\x1b[1;33m║       CTF SCOREBOARD                 ║\x1b[0m",
            "\x1b[1;33m╠══════════════════════════════════════╣\x1b[0m",
            f"\x1b[1;33m║\x1b[0m  Player: \x1b[1;32m{self.current_user:<20s}\x1b[0m    \x1b[1;33m║\x1b[0m",
            f"\x1b[1;33m║\x1b[0m  Score:  \x1b[1;32m{self.score}\x1b[0m / \x1b[37m{MAX_SCORE:<15d}\x1b[0m   \x1b[1;33m║\x1b[0m",
            f"\x1b[1;33m║\x1b[0m  Flags:  \x1b[1;32m{len(self.found_flags)}\x1b[0m / \x1b[37m{len(FLAGS):<15d}\x1b[0m   \x1b[1;33m║\x1b[0m",
            f"\x1b[1;33m║\x1b[0m  Time:   \x1b[37m{mins}m {secs}s\x1b[0m                    \x1b[1;33m║\x1b[0m",
            "\x1b[1;33m╠══════════════════════════════════════╣\x1b[0m",
        ]
        # Show found flags
        if self.found_flags:
            lines.append("\x1b[1;33m║\x1b[0m  \x1b[1;32mFLAGS CAPTURED:\x1b[0m                    \x1b[1;33m║\x1b[0m")
            for path in sorted(self.found_flags):
                pts = FLAGS[path]['points']
                short = path.split('/')[-1]
                lines.append(f"\x1b[1;33m║\x1b[0m   \x1b[32m✓\x1b[0m {short:<20s} \x1b[32m+{pts}pts\x1b[0m  \x1b[1;33m║\x1b[0m")
        else:
            lines.append("\x1b[1;33m║\x1b[0m  \x1b[90mNo flags captured yet.\x1b[0m          \x1b[1;33m║\x1b[0m")
        lines.append("\x1b[1;33m╚══════════════════════════════════════╝\x1b[0m")
        return "\n".join(lines)

    def _cmd_history(self, args):
        if not self.history:
            return ""
        lines = []
        for i, cmd in enumerate(self.history, 1):
            lines.append(f"  {i:4d}  {cmd}")
        return "\n".join(lines)

    def _cmd_ifconfig(self, args):
        import random
        return f"""eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 192.168.1.{random.randint(10, 200)}  netmask 255.255.255.0  broadcast 192.168.1.255
        inet6 fe80::a00:27ff:fe8e:1234  prefixlen 64  scopeid 0x20<link>
        ether 08:00:27:8e:12:34  txqueuelen 1000  (Ethernet)
        RX packets 45832  bytes 34521890 (34.5 MB)
        TX packets 23451  bytes 8723456 (8.7 MB)

lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536
        inet 127.0.0.1  netmask 255.0.0.0
        inet6 ::1  prefixlen 128  scopeid 0x10<host>
        loop  txqueuelen 1000  (Local Loopback)
        RX packets 1234  bytes 102400 (102.4 KB)
        TX packets 1234  bytes 102400 (102.4 KB)"""

    def _cmd_netstat(self, args):
        import random
        lines = [
            "Active Internet connections (servers and established)",
            "Proto Recv-Q Send-Q Local Address           Foreign Address         State",
            "tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN",
            "tcp        0      0 0.0.0.0:80              0.0.0.0:*               LISTEN",
            f"tcp        0      0 192.168.1.{random.randint(10,200)}:22       10.0.0.{random.randint(1,254)}:{random.randint(40000,65000)}     ESTABLISHED",
            f"tcp        0      0 192.168.1.{random.randint(10,200)}:80       10.0.0.{random.randint(1,254)}:{random.randint(40000,65000)}     ESTABLISHED",
            "tcp6       0      0 :::443                  :::*                    LISTEN",
            "udp        0      0 0.0.0.0:68              0.0.0.0:*               ",
        ]
        return "\n".join(lines)

    def _cmd_ps(self, args):
        lines = [
            "  PID TTY          TIME CMD",
            "    1 ?        00:00:03 systemd",
            "  234 ?        00:00:00 sshd",
            "  567 ?        00:00:01 apache2",
            "  890 ?        00:00:00 cron",
            " 1234 pts/0    00:00:00 bash",
            f" {1235} pts/0    00:00:00 ps",
        ]
        if args and ("-aux" in args or "aux" in args):
            lines = [
                "USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND",
                "root           1  0.0  0.4 169124 13200 ?        Ss   10:00   0:03 /sbin/init",
                "root         234  0.0  0.2  15432  5048 ?        Ss   10:00   0:00 sshd: /usr/sbin/sshd",
                "root         567  0.0  0.5  78432 17600 ?        Ss   10:00   0:01 /usr/sbin/apache2 -k start",
                "www-data     568  0.0  0.3  78432 12100 ?        S    10:00   0:00 /usr/sbin/apache2 -k start",
                "root         890  0.0  0.1   8536  3200 ?        Ss   10:00   0:00 /usr/sbin/cron -f",
                f"{self.current_user}      1234  0.0  0.2  10048  6200 pts/0    Ss   10:05   0:00 -bash",
                f"{self.current_user}      1235  0.0  0.1   7648  2400 pts/0    R+   10:05   0:00 ps aux",
            ]
        return "\n".join(lines)

