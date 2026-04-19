import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, Toplevel
from tkinter import ttk
import git
import os
import time
import json
import pyperclip
import webbrowser
import sqlite3
import shutil
import stat
from datetime import datetime

class GitCreatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("KDSN Git Helper - 终极流水线版 (带 AI 防爆盾)")
        self.root.geometry("620x800") 
        
        self.config_file = "git_helper_config.json"
        self.config_data = self.load_config()
        self.colors = {
            "flash1": "#FFFF00", "flash2": "#800080",
            "current": "#2E7D32", "blue": "#2196F3", "gray": "gray",
            "repo_name": "#D32F2F",
            "alert": "#E65100"
        }

        self.repo_path = tk.StringVar()
        self.remote_url = tk.StringVar()
        self.last_branch = "无"
        self.curr_branch = "无"

        self.init_database()
        self.setup_ui()
        self.load_recent_logs()
        self.auto_load_last_project()

    def init_database(self):
        self.db_conn = sqlite3.connect("git_helper_data.db", check_same_thread=False)
        self.cursor = self.db_conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS logs
                               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                time TEXT,
                                message TEXT)''')
        self.db_conn.commit()

    def setup_ui(self):
        tk.Button(self.root, text="⚙️ 仓库配置 (需配置远程 URL 才能生链接)", command=self.open_settings, font=('Arial', 9)).pack(fill="x", padx=15, pady=(10, 5))

        # ====== 双状态面板 ======
        self.frame_last = tk.LabelFrame(self.root, text=" 上次状态 ", fg=self.colors["gray"], font=('微软雅黑', 9))
        self.frame_last.pack(fill="x", padx=15, pady=5)
        
        last_info_frame = tk.Frame(self.frame_last, cursor="hand2")
        last_info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        
        self.lbl_last_repo = tk.Label(last_info_frame, text="📁 仓库: 无", fg="gray", font=("微软雅黑", 9))
        self.lbl_last_repo.pack(anchor="w")
        self.lbl_last_branch = tk.Label(last_info_frame, text="🌿 分支: 无", font=("Consolas", 10), fg="gray")
        self.lbl_last_branch.pack(anchor="w")
        self.lbl_last_status = tk.Label(last_info_frame, text="...", fg="gray", font=("微软雅黑", 9))
        self.lbl_last_status.pack(anchor="w")

        last_btn_frame = tk.Frame(self.frame_last)
        last_btn_frame.pack(side="right", padx=10, pady=5)
        self.btn_last_web = tk.Button(last_btn_frame, text="🌐 查看", command=lambda: self.open_branch_web("last"), state="disabled")
        self.btn_last_web.pack(fill="x", pady=2)
        self.btn_last_copy = tk.Button(last_btn_frame, text="🔗 复制链接", command=lambda: self.copy_branch_url("last"), state="disabled")
        self.btn_last_copy.pack(fill="x", pady=2)

        self.frame_curr = tk.LabelFrame(self.root, text=" 当前实时状态 ", fg=self.colors["blue"], font=('微软雅黑', 10, 'bold'))
        self.frame_curr.pack(fill="x", padx=15, pady=5)
        
        curr_info_frame = tk.Frame(self.frame_curr, cursor="hand2")
        curr_info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        
        self.lbl_curr_repo = tk.Label(curr_info_frame, text="📁 仓库: [等待选择]", fg=self.colors["repo_name"], font=("微软雅黑", 10, "bold"))
        self.lbl_curr_repo.pack(anchor="w")
        self.lbl_curr_branch = tk.Label(curr_info_frame, text="🌿 分支: 无", font=("Consolas", 12, "bold"), fg="black")
        self.lbl_curr_branch.pack(anchor="w")
        self.lbl_curr_status = tk.Label(curr_info_frame, text="请检测状态...", font=("微软雅黑", 10))
        self.lbl_curr_status.pack(anchor="w")

        curr_btn_frame = tk.Frame(self.frame_curr)
        curr_btn_frame.pack(side="right", padx=10, pady=5)
        self.btn_curr_web = tk.Button(curr_btn_frame, text="🌐 查看", command=lambda: self.open_branch_web("curr"), state="disabled")
        self.btn_curr_web.pack(fill="x", pady=2)
        self.btn_curr_copy = tk.Button(curr_btn_frame, text="🔗 复制链接", command=lambda: self.copy_branch_url("curr"), font=('Arial', 9, 'bold'), state="disabled")
        self.btn_curr_copy.pack(fill="x", pady=2)

        for target in [last_info_frame, self.lbl_last_repo, self.lbl_last_branch, self.lbl_last_status]:
            target.bind("<Button-1>", lambda e: self.copy_branch_and_flash("last"))
        for target in [curr_info_frame, self.lbl_curr_repo, self.lbl_curr_branch, self.lbl_curr_status]:
            target.bind("<Button-1>", lambda e: self.copy_branch_and_flash("curr"))

        # --- 下拉框选择路径 ---
        path_frame = tk.Frame(self.root)
        path_frame.pack(fill="x", padx=15, pady=10)
        
        self.combo_path = ttk.Combobox(path_frame, textvariable=self.repo_path, state='readonly', font=('Arial', 9))
        self.combo_path.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.combo_path.bind("<<ComboboxSelected>>", self.on_combo_select)
        
        tk.Button(path_frame, text="📁 浏览新目录", command=self.select_dir).pack(side="right")

        # --- 核心流水线 ---
        flow_frame = tk.LabelFrame(self.root, text="🚀 核心流水线", padx=15, pady=10)
        flow_frame.pack(fill="x", padx=15, pady=5)

        self.btn_pipeline = tk.Button(flow_frame, text="📦 一键打包上云\n(建时间分支 ➔ 提交 ➔ 推送)", 
                                      bg="#e3f2fd", font=('微软雅黑', 10, 'bold'), command=self.run_one_click_pipeline, height=2)
        self.btn_pipeline.pack(fill="x", pady=2)
        
        self.lbl_gui_alert = tk.Label(flow_frame, text="", font=("微软雅黑", 10, "bold"))
        self.lbl_gui_alert.pack(fill="x")

        # --- 日志控制条 ---
        log_ctrl_frame = tk.Frame(self.root)
        log_ctrl_frame.pack(fill="x", padx=15, pady=(5, 0))
        tk.Label(log_ctrl_frame, text="📄 操作日志", font=('微软雅黑', 9, 'bold'), fg="gray").pack(side="left")
        
        tk.Button(log_ctrl_frame, text="🧹 清空", command=self.clear_logs, font=('微软雅黑', 8), cursor="hand2", bg="#f5f5f5").pack(side="right", padx=(5, 0))
        tk.Button(log_ctrl_frame, text="📋 复制全部", command=self.copy_all_logs, font=('微软雅黑', 8), cursor="hand2", bg="#e8f5e9").pack(side="right")

        # --- 日志区域 ---
        self.log_area = scrolledtext.ScrolledText(self.root, height=12, font=('Consolas', 9))
        self.log_area.pack(fill="both", padx=15, pady=(2, 10), expand=True)

    def show_gui_alert(self, message, color):
        self.lbl_gui_alert.config(text=message, fg=color)
        self.root.after(4000, lambda: self.lbl_gui_alert.config(text=""))

    def load_recent_logs(self):
        try:
            self.log_area.delete('1.0', tk.END)
            self.cursor.execute("SELECT time, message FROM logs ORDER BY id DESC LIMIT 15")
            rows = self.cursor.fetchall()
            if rows:
                for row in rows:
                    self.log_area.insert(tk.END, f"[{row[0]}] {row[1]}\n")
                self.log_area.insert(tk.END, "--- 以上为数据库历史记录 ---\n")
        except Exception as e:
            pass

    def log(self, message):
        full_time = time.strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{full_time}] {message}\n"
        
        self.log_area.insert('1.0', log_line)
        self.log_area.see('1.0') 
        
        try:
            self.cursor.execute("INSERT INTO logs (time, message) VALUES (?, ?)", (full_time, message))
            self.db_conn.commit()
        except: pass

    def clear_logs(self):
        self.log_area.delete('1.0', tk.END)
        try:
            self.cursor.execute("DELETE FROM logs")
            self.db_conn.commit()
        except: pass
        try:
            with open("git_helper_history.log", "w", encoding="utf-8") as f:
                pass 
        except: pass
        self.log("🧹 历史日志已瞬间清空。")

    def copy_all_logs(self):
        content = self.log_area.get('1.0', tk.END).strip()
        if content:
            pyperclip.copy(content)
            self.show_gui_alert("📋 日志已全部复制到剪贴板！", self.colors["current"])
        else:
            self.show_gui_alert("⚠️ 日志为空", self.colors["alert"])

    def update_combo_values(self):
        paths = [p for p in self.config_data.keys() if p != "last_opened" and os.path.exists(p)]
        self.combo_path['values'] = paths

    def auto_load_last_project(self):
        self.update_combo_values()
        if "last_opened" in self.config_data:
            last_path = self.config_data["last_opened"]
            if os.path.exists(last_path):
                self.repo_path.set(last_path)
                self.remote_url.set(self.config_data.get(last_path, ""))
                self.update_status()
                self.log(f"🔄 自动恢复上次项目: {os.path.basename(last_path)}")
                return
        for path in self.config_data.keys():
            if path != "last_opened" and os.path.exists(path):
                self.repo_path.set(path)
                self.remote_url.set(self.config_data[path])
                self.update_status()
                self.log(f"🔄 自动恢复项目: {os.path.basename(path)}")
                break

    # --- 【重点升级：AI 防爆盾】全自动拦截与清洗垃圾文件 ---
    def enforce_gitignore(self, repo, path):
        # 1. 定义我们要拦截的“AI 杀手”文件和目录
        ignores = [
            '# Git Helper 自身文件',
            'git_helper_history.log', 'git_helper_config.json', 'git_helper_data.db',
            '# Python 打包与编译垃圾',
            '__pycache__/', '*.pyc', 'build/', 'dist/', '*.exe', '*.spec',
            '# 自动化测试与浏览器缓存 (webqu 专属)',
            'browser_data/', 'browser_data_safe/',
            '# 虚拟环境与前端依赖',
            'venv/', '.venv/', 'node_modules/'
        ]
        
        gitignore_path = os.path.join(path, '.gitignore')
        content = ""
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        # 2. 将缺失的规则追加进 .gitignore
        with open(gitignore_path, 'a', encoding='utf-8') as f:
            for item in ignores:
                if item not in content:
                    if content and not content.endswith('\n'):
                        f.write("\n")
                    f.write(f"{item}\n")
                    content += f"{item}\n"
        
        # 3. 强力清洗：如果这些垃圾之前已经不小心提交过了，用 rm --cached 踢出索引
        try:
            # 遍历核心的危险目录进行清理
            for junk in ['__pycache__', 'build', 'dist', 'browser_data', 'browser_data_safe', '*.pyc', '*.exe', 'git_helper_history.log', 'git_helper_config.json', 'git_helper_data.db']:
                try:
                    repo.git.rm('-r', '--cached', junk, ignore_unmatch=True)
                except:
                    pass # 如果本来就不在缓存里，静默忽略
        except: pass

    def copy_branch_and_flash(self, mode):
        if mode == "last":
            branch = self.last_branch
            target_frame = self.frame_last
            target_lbl = self.lbl_last_branch
        else:
            branch = self.curr_branch
            target_frame = self.frame_curr
            target_lbl = self.lbl_curr_branch

        if branch and branch != "无" and "获取失败" not in branch:
            pyperclip.copy(branch)
            self.flash_effect(target_frame, target_lbl, mode, 0)
            self.log(f"📋 已复制分支名: {branch}")

    def flash_effect(self, frame, lbl, mode, stage):
        sequence = [self.colors["flash1"], self.colors["flash2"], self.colors["flash1"], self.colors["flash2"]]
        orig_fg = self.colors["blue"] if mode == "curr" else self.colors["gray"]
        orig_lbl_fg = "black" if mode == "curr" else self.colors["gray"]
        
        if stage < len(sequence):
            frame.config(fg=sequence[stage])
            lbl.config(fg=sequence[stage])
            self.root.after(120, lambda: self.flash_effect(frame, lbl, mode, stage + 1))
        else:
            frame.config(fg=orig_fg)
            lbl.config(fg=orig_lbl_fg)

    def copy_branch_url(self, mode):
        url = self.remote_url.get().replace('.git', '')
        branch = self.last_branch if mode == "last" else self.curr_branch
        if url and branch and branch != "无":
            full_url = f"{url}/tree/{branch}"
            pyperclip.copy(full_url)
            self.log(f"🔗 已复制网页链接，可直接发送给 AI！")
            self.show_gui_alert(f"✅ {mode} 状态网页链接已复制！", self.colors["current"])

    def open_branch_web(self, mode):
        url = self.remote_url.get().replace('.git', '')
        branch = self.last_branch if mode == "last" else self.curr_branch
        if url and branch and branch != "无":
            webbrowser.open(f"{url}/tree/{branch}")
            self.log("🌐 已在浏览器中打开分支")

    def get_formatted_time(self):
        now = datetime.now()
        return f"{now.year}-{now.month}-{now.day}--{now.strftime('%H-%M-%S')}"

    def update_status(self):
        path = self.repo_path.get()
        if path and os.path.exists(os.path.join(path, '.git')):
            repo_name = os.path.basename(path)
            self.lbl_curr_repo.config(text=f"📁 仓库: [{repo_name}]")
            try:
                repo = git.Repo(path)
                self.enforce_gitignore(repo, path)
                
                self.curr_branch = repo.active_branch.name
                self.lbl_curr_branch.config(text=f"🌿 分支: {self.curr_branch}")
                
                status_raw = repo.git.status()
                is_clean = "nothing to commit, working tree clean" in status_raw
                clean_msg = "✅ 现场干净，无需重复打包" if is_clean else "⚠️ 有新改动，请点击打包上云"
                self.lbl_curr_status.config(text=clean_msg)
                
                has_url = bool(self.remote_url.get())
                self.btn_curr_web.config(state="normal" if has_url else "disabled")
                self.btn_curr_copy.config(state="normal" if is_clean and has_url else "disabled")
                
            except:
                self.lbl_curr_branch.config(text="🌿 分支: 获取失败")
                self.lbl_curr_status.config(text="❌ 仓库读取异常")
        else:
            repo_name = os.path.basename(path) if path else "未选择"
            self.lbl_curr_repo.config(text=f"📁 仓库: [{repo_name}]")
            self.lbl_curr_branch.config(text="🌿 分支: 无")
            self.lbl_curr_status.config(text="未初始化 Git 仓库 (请点击右上角配置 URL)")
            self.btn_curr_web.config(state="disabled")
            self.btn_curr_copy.config(state="disabled")

    def run_one_click_pipeline(self):
        path = self.repo_path.get()
        url = self.remote_url.get()
        if not path or not url: 
            self.show_gui_alert("❌ 请先配置本地仓库和远程 URL！", "red")
            return
            
        try:
            if not os.path.exists(os.path.join(path, '.git')):
                git.Repo.init(path)
                self.log(f"🌱 发现空白状态，流水线已自动为你执行 git init")
                self.update_status() 

            repo = git.Repo(path)
            status_raw = repo.git.status()
            is_clean = "nothing to commit, working tree clean" in status_raw
            
            if is_clean:
                if not messagebox.askyesno("异常同步提示", "当前代码没有检测到任何新改动。\n\n如果您刚刚删除了云端仓库并重新创建，或者由于其他原因云端数据丢失，请点击【是】强行新建时间分支并同步。\n\n否则请点击【否】取消操作。"):
                    self.show_gui_alert("🛡️ 已取消打包推送。", self.colors["alert"])
                    return
                else:
                    self.log("⚠️ 触发强制同步模式...")

            self.show_gui_alert("⏳ 正在创建时间分支并推送至云端...", "blue")
            self.root.update()

            self.last_branch = self.curr_branch
            self.lbl_last_repo.config(text=self.lbl_curr_repo.cget("text"))
            self.lbl_last_branch.config(text=self.lbl_curr_branch.cget("text"))
            self.lbl_last_status.config(text="✅ 历史状态归档")
            self.btn_last_web.config(state="normal")
            self.btn_last_copy.config(state="normal")

            branch_name = self.get_formatted_time()
            try:
                repo.git.checkout('-b', branch_name)
            except Exception:
                repo.git.checkout('-B', branch_name)

            repo.git.add(A=True)
            repo.index.commit(f"Auto Wrap: {branch_name}")

            self.log(f"📡 正在尝试连线推送到: {url}")
            
            origin = repo.remote('origin') if 'origin' in repo.remotes else repo.create_remote('origin', url)
            origin.set_url(url)
            origin.push(branch_name, force=True, set_upstream=True)

            self.update_status()
            self.copy_branch_url("curr")
            
            self.show_gui_alert("✅ 时间分支打包上云成功！", self.colors["current"])
            self.log("✅ 代码流水线执行完毕，新时间分支已上云。")

        except Exception as e:
            self.log(f"❌ 流水线失败: {e}")
            self.show_gui_alert("❌ 推送失败，详情请看日志", "red")

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f: return json.load(f)
        return {}

    def save_config(self):
        self.config_data["last_opened"] = self.repo_path.get()
        with open(self.config_file, 'w') as f: json.dump(self.config_data, f)
        self.update_combo_values() 

    def on_combo_select(self, event):
        path = self.repo_path.get()
        if path and os.path.exists(path):
            self.remote_url.set(self.config_data.get(path, ""))
            
            self.last_branch = "无"
            self.lbl_last_repo.config(text="📁 仓库: 无")
            self.lbl_last_branch.config(text="🌿 分支: 无")
            self.lbl_last_status.config(text="...")
            self.btn_last_web.config(state="disabled")
            self.btn_last_copy.config(state="disabled")
            
            self.update_status()
            self.save_config() 
            self.log(f"📂 下拉切换项目至: {os.path.basename(path)}")

    def select_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.repo_path.set(path)
            self.remote_url.set(self.config_data.get(path, ""))
            
            self.last_branch = "无"
            self.lbl_last_repo.config(text="📁 仓库: 无")
            self.lbl_last_branch.config(text="🌿 分支: 无")
            self.lbl_last_status.config(text="...")
            self.btn_last_web.config(state="disabled")
            self.btn_last_copy.config(state="disabled")
            
            self.update_status()
            self.save_config() 
            self.log(f"📁 浏览切换项目至: {os.path.basename(path)}")

    def remove_readonly(self, func, path, _):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    def delete_git_folder(self, win):
        path = self.repo_path.get()
        git_dir = os.path.join(path, '.git')
        
        if not os.path.exists(git_dir):
            messagebox.showinfo("提示", "当前目录干净清爽，不存在 .git 记忆，无需删除。")
            return
            
        if messagebox.askyesno("🔥 终极警告", "确定要彻底删除本地的 .git 记忆吗？\n\n这会清空所有本地 Git 提交历史，但【绝对不会】删除你的任何代码文件！\n\n物理超度后，下次打包将作为全新的项目推送到云端！"):
            try:
                shutil.rmtree(git_dir, onerror=self.remove_readonly)
                self.log(f"🔥 已成功摧毁本地影子库记忆: {os.path.basename(path)}")
                self.update_status() 
                win.destroy() 
                messagebox.showinfo("超度成功", "本地影子库已被彻底物理粉碎！\n\n系统已进入无感复活模式，请直接点击【📦 一键打包上云】，一切将自动从零开始！")
            except Exception as e:
                messagebox.showerror("删除失败", f"删除 .git 文件夹时出错，请确保没有其他软件（如 VSCode）正在占用该文件夹:\n{e}")

    def open_settings(self):
        path = self.repo_path.get()
        if not path: return
        win = Toplevel(self.root)
        win.title("仓库配置与高级管理")
        win.geometry("500x260")
        
        repo_name = os.path.basename(path)
        tk.Label(win, text=f"当前操作仓库: [{repo_name}]", font=("微软雅黑", 14, "bold"), fg="red").pack(pady=(15, 10))
        
        tk.Label(win, text="远程 GitHub URL:").pack(pady=5)
        ent = tk.Entry(win, textvariable=self.remote_url, width=50)
        ent.pack(pady=5)
        
        btn_frame = tk.Frame(win)
        btn_frame.pack(pady=20, fill="x", padx=20)
        
        tk.Button(btn_frame, text="💾 保存 URL 配置", command=lambda: self.save_and_init(win), bg="#e3f2fd", font=("微软雅黑", 9, "bold"), height=2).pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        tk.Button(btn_frame, text="🔥 删除 .git 记忆", command=lambda: self.delete_git_folder(win), bg="#ffebee", fg="red", font=("微软雅黑", 9, "bold"), height=2).pack(side="right", expand=True, fill="x", padx=(5, 0))

    def save_and_init(self, win):
        path = self.repo_path.get()
        self.config_data[path] = self.remote_url.get()
        self.save_config()
        if not os.path.exists(os.path.join(path, '.git')):
            git.Repo.init(path)
            self.log(f"🌱 自动为 {os.path.basename(path)} 初始化了全新的 Git 仓库")
        win.destroy()
        self.update_status()

if __name__ == "__main__":
    root = tk.Tk()
    app = GitCreatorGUI(root)
    root.mainloop()