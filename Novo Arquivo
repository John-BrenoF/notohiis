import subprocess
import os
import re
import logging
from urllib.parse import quote

logger = logging.getLogger("GitLogic")

class GitLogic:
    """Gerencia operações do Git, isolando a lógica de sistema da UI."""

    def clone_repository(self, repo_url: str, destination_folder: str) -> tuple[bool, str]:
        """
        Executa o comando git clone.
        Retorna: (sucesso: bool, mensagem: str)
        """
        if not repo_url or not destination_folder:
            return False, "URL e pasta de destino são obrigatórios."

        try:
            # Executa o git clone no diretório escolhido
            # check=True levanta exceção se o comando falhar
            env = os.environ.copy()
            env["GIT_TERMINAL_PROMPT"] = "0"
            subprocess.run(["git", "clone", repo_url], cwd=destination_folder, check=True, capture_output=True, env=env)
            return True, f"Repositório clonado com sucesso em: {destination_folder}"
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().strip() if e.stderr else "Erro desconhecido"
            return False, f"Erro ao clonar: {error_msg}"
        except Exception as e:
            return False, f"Erro de sistema: {str(e)}"

    def is_repo(self, path: str) -> bool:
        """Verifica se o caminho é um repositório git."""
        try:
            # Usa git rev-parse para verificar se estamos dentro de uma árvore de trabalho git
            # Isso funciona mesmo se abrirmos uma subpasta do repositório
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"], 
                cwd=path, 
                check=True, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_current_branch(self, repo_path: str) -> str:
        try:
            res = subprocess.run(["git", "branch", "--show-current"], cwd=repo_path, capture_output=True, text=True)
            return res.stdout.strip()
        except:
            return "HEAD"

    def get_graph_data(self, repo_path: str) -> list:
        """Retorna lista de commits formatada para o gráfico."""
        # Separador único para evitar conflito com mensagens de commit
        sep = "^@^"
        cmd = ["git", "log", "--all", "--date=short", f"--pretty=format:%h{sep}%p{sep}%s{sep}%cd{sep}%an{sep}%d", "-n", "100"]
        
        try:
            result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if result.returncode != 0:
                return []
                
            commits = []
            for line in result.stdout.splitlines():
                parts = line.split(sep)
                if len(parts) < 6: continue
                
                commits.append({
                    "hash": parts[0],
                    "parents": parts[1].split(),
                    "message": parts[2],
                    "date": parts[3],
                    "author": parts[4],
                    "refs": parts[5].strip()
                })
            return commits
        except Exception as e:
            logger.error(f"Git graph error: {e}")
            return []

    def stage_all(self, repo_path: str):
        """Adiciona todos os arquivos modificados ao stage."""
        subprocess.run(["git", "add", "."], cwd=repo_path, check=False)

    def commit(self, repo_path: str, message: str) -> tuple[bool, str]:
        """Realiza um commit com todos os arquivos modificados."""
        if not message: return False, "Mensagem de commit vazia."
        try:
            self.stage_all(repo_path)
            subprocess.run(["git", "commit", "-m", message], cwd=repo_path, check=True, capture_output=True)
            return True, "Commit realizado com sucesso."
        except subprocess.CalledProcessError as e:
            return False, f"Erro no commit: {e.stderr.decode() if e.stderr else str(e)}"

    def create_branch(self, repo_path: str, branch_name: str) -> tuple[bool, str]:
        try:
            subprocess.run(["git", "checkout", "-b", branch_name], cwd=repo_path, check=True, capture_output=True)
            return True, f"Branch '{branch_name}' criado e ativo."
        except subprocess.CalledProcessError as e:
            return False, f"Erro ao criar branch: {e.stderr.decode() if e.stderr else str(e)}"

    def get_remote_url(self, repo_path: str, remote: str = "origin") -> str:
        try:
            res = subprocess.run(["git", "remote", "get-url", remote], cwd=repo_path, capture_output=True, text=True)
            return res.stdout.strip()
        except:
            return ""

    def _inject_credentials(self, url: str, username: str, token: str) -> str:
        if "://" not in url: return url
        protocol, rest = url.split("://", 1)
        if "@" in rest:
            rest = rest.split("@", 1)[1]
            
        # Codifica username e token para lidar com caracteres especiais (ex: '@', ':')
        safe_username = quote(username, safe='')
        safe_token = quote(token, safe='')
        return f"{protocol}://{safe_username}:{safe_token}@{rest}"

    def push(self, repo_path: str, username: str = None, token: str = None) -> tuple[bool, str]:
        try:
            cmd = ["git", "push"]
            if username and token:
                url = self.get_remote_url(repo_path)
                if url.startswith("http"):
                    auth_url = self._inject_credentials(url, username, token)
                    cmd = ["git", "push", auth_url]
            
            env = os.environ.copy()
            env["GIT_TERMINAL_PROMPT"] = "0"
            subprocess.run(cmd, cwd=repo_path, check=True, capture_output=True, env=env)
            return True, "Push realizado com sucesso."
        except subprocess.CalledProcessError as e:
            return False, f"Erro no Push: {e.stderr.decode() if e.stderr else str(e)}"

    def pull(self, repo_path: str, username: str = None, token: str = None) -> tuple[bool, str]:
        try:
            cmd = ["git", "pull"]
            if username and token:
                url = self.get_remote_url(repo_path)
                if url.startswith("http"):
                    auth_url = self._inject_credentials(url, username, token)
                    cmd = ["git", "pull", auth_url]

            env = os.environ.copy()
            env["GIT_TERMINAL_PROMPT"] = "0"
            subprocess.run(cmd, cwd=repo_path, check=True, capture_output=True, env=env)
            return True, "Pull realizado com sucesso."
        except subprocess.CalledProcessError as e:
            return False, f"Erro no Pull: {e.stderr.decode() if e.stderr else str(e)}"

    def get_branches(self, repo_path: str) -> list[str]:
        try:
            res = subprocess.run(["git", "branch", "--format=%(refname:short)"], cwd=repo_path, capture_output=True, text=True)
            return [b.strip() for b in res.stdout.split('\n') if b.strip()]
        except:
            return []

    def checkout(self, repo_path: str, branch_name: str) -> tuple[bool, str]:
        try:
            subprocess.run(["git", "checkout", branch_name], cwd=repo_path, check=True, capture_output=True)
            return True, f"Checkout para '{branch_name}' realizado."
        except subprocess.CalledProcessError as e:
            return False, f"Erro no Checkout: {e.stderr.decode() if e.stderr else str(e)}"

    def get_commit_files(self, repo_path: str, commit_hash: str) -> list[str]:
        try:
            res = subprocess.run(["git", "show", "--pretty=", "--name-only", commit_hash], cwd=repo_path, capture_output=True, text=True)
            return [f for f in res.stdout.split('\n') if f.strip()]
        except:
            return []

    def get_diff(self, repo_path: str, commit_hash: str, file_path: str) -> str:
        try:
            res = subprocess.run(["git", "show", commit_hash, "--", file_path], cwd=repo_path, capture_output=True, text=True)
            return res.stdout
        except:
            return "Não foi possível obter o diff."

    def get_commit_stats(self, repo_path: str, commit_hash: str) -> dict:
        """
        Retorna estatísticas de um commit específico (arquivos alterados, inserções, deleções).
        """
        try:
            # Tenta com 'git show' primeiro, que funciona para a maioria dos commits
            cmd = ["git", "show", commit_hash, "--shortstat", "--pretty="]
            res = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
            
            stat_line = ""
            output_lines = res.stdout.strip().splitlines()
            if output_lines:
                # A linha de stats é geralmente a última linha não vazia
                for line in reversed(output_lines):
                    if "changed" in line:
                        stat_line = line.strip()
                        break
            
            files_match = re.search(r'(\d+)\s+file', stat_line)
            insertions_match = re.search(r'(\d+)\s+insertion', stat_line)
            deletions_match = re.search(r'(\d+)\s+deletion', stat_line)
            
            return {
                "files": int(files_match.group(1)) if files_match else 0,
                "insertions": int(insertions_match.group(1)) if insertions_match else 0,
                "deletions": int(deletions_match.group(1)) if deletions_match else 0
            }
        except Exception as e:
            logger.error(f"Erro ao obter stats do commit {commit_hash}: {e}")
            # Retorna -1 para indicar que houve um erro ao buscar os dados
            return {"files": -1, "insertions": -1, "deletions": -1}

    def get_staged_files(self, repo_path: str) -> list[str]:
        """Retorna lista de arquivos na área de stage."""
        try:
            res = subprocess.run(["git", "status", "--porcelain"], cwd=repo_path, capture_output=True, text=True)
            files = []
            for line in res.stdout.splitlines():
                if len(line) > 3:
                    status = line[:2]
                    # Se o primeiro caractere (index) não for espaço nem '?', está staged
                    if status[0] not in (' ', '?'):
                        files.append(line[3:])
            return files
        except:
            return []

    def get_unstaged_files(self, repo_path: str) -> list[str]:
        """Retorna lista de arquivos modificados fora do stage."""
        try:
            res = subprocess.run(["git", "status", "--porcelain"], cwd=repo_path, capture_output=True, text=True)
            files = []
            for line in res.stdout.splitlines():
                if len(line) > 3:
                    status = line[:2]
                    # Se o segundo caractere (worktree) não for espaço, ou for untracked '??'
                    if status[1] != ' ' or status == '??':
                        files.append(line[3:])
            return files
        except:
            return []

    def get_working_diff(self, repo_path: str, file_path: str) -> str:
        """Retorna o diff do arquivo no diretório de trabalho (vs Index)."""
        try:
            res = subprocess.run(["git", "diff", "--", file_path], cwd=repo_path, capture_output=True, text=True)
            return res.stdout
        except:
            return "Não foi possível obter o diff."

    def get_staged_diff(self, repo_path: str, file_path: str) -> str:
        """Retorna o diff do arquivo no stage (vs HEAD)."""
        try:
            res = subprocess.run(["git", "diff", "--cached", "--", file_path], cwd=repo_path, capture_output=True, text=True)
            return res.stdout
        except:
            return "Não foi possível obter o diff."

    def discard_changes(self, repo_path: str, file_path: str) -> tuple[bool, str]:
        """Descarta alterações no arquivo (reverte para HEAD ou exclui se for novo)."""
        try:
            # Verifica se é arquivo novo (untracked)
            status_res = subprocess.run(["git", "status", "--porcelain", file_path], cwd=repo_path, capture_output=True, text=True)
            if status_res.stdout.startswith("??"):
                os.remove(os.path.join(repo_path, file_path))
                return True, "Arquivo novo excluído."
            
            # Para arquivos modificados/deletados
            subprocess.run(["git", "checkout", "HEAD", "--", file_path], cwd=repo_path, check=True, capture_output=True)
            return True, "Alterações descartadas."
        except Exception as e:
            return False, f"Erro ao descartar: {str(e)}"

    def stage_file(self, repo_path: str, file_path: str) -> tuple[bool, str]:
        """Adiciona um arquivo específico ao stage (git add)."""
        try:
            subprocess.run(["git", "add", file_path], cwd=repo_path, check=True, capture_output=True)
            return True, "Arquivo adicionado ao stage."
        except subprocess.CalledProcessError as e:
            return False, f"Erro ao adicionar ao stage: {e.stderr.decode() if e.stderr else str(e)}"

    def get_files_stats(self, repo_path: str, staged: bool = False) -> dict:
        """Retorna estatísticas de linhas (+/-)."""
        stats = {}
        try:
            cmd = ["git", "diff", "--numstat"]
            if staged:
                cmd.append("--cached")
            res = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
            for line in res.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        added = int(parts[0])
                        removed = int(parts[1])
                        filename = " ".join(parts[2:])
                        stats[filename] = (added, removed)
                    except ValueError:
                        pass # Ignora arquivos binários ou erros de parse
            return stats
        except:
            return {}

    def unstage_file(self, repo_path: str, file_path: str) -> tuple[bool, str]:
        """Remove um arquivo do stage (git reset HEAD)."""
        try:
            subprocess.run(["git", "reset", "HEAD", "--", file_path], cwd=repo_path, check=True, capture_output=True)
            return True, "Arquivo removido do stage."
        except subprocess.CalledProcessError as e:
            return False, f"Erro ao remover do stage: {e.stderr.decode() if e.stderr else str(e)}"

    def count_project_lines(self, repo_path: str) -> tuple[int, int]:
        """
        Conta o número total de linhas em todos os arquivos rastreados, respeitando .gitignore.
        Retorna: (total_files, total_lines)
        """
        try:
            # git ls-files lista todos os arquivos rastreados pelo git, respeitando automaticamente .gitignore
            res = subprocess.run(["git", "ls-files"], cwd=repo_path, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
            files = res.stdout.splitlines()
            
            total_lines = 0
            file_count = len(files)

            for file_path in files:
                full_path = os.path.join(repo_path, file_path)
                if not os.path.isfile(full_path):
                    continue
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        total_lines += sum(1 for _ in f)
                except Exception:
                    # Ignora arquivos binários ou com erros de codificação
                    continue
            
            return file_count, total_lines
        except (subprocess.CalledProcessError, FileNotFoundError):
            return 0, 0
        except Exception as e:
            logger.error(f"Erro ao contar linhas do projeto: {e}")
            return 0, 0