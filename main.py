#!/usr/bin/env python3
"""
Hierarchical Portfolio Generator: 
Generates a Master Company Dashboard that links to individual Repo Dashboards, 
which in turn link to individual Full Commit Histories.
Features bi-directional navigation, customizable CTAs, and nested folder structure.
"""

import subprocess
import re
import os
import json
from datetime import datetime, timedelta
from collections import Counter
import argparse
import sys

import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

# ==========================================
# PHASE 1: DATA EXTRACTION
# ==========================================
class GitMetricsExtractor:
    def __init__(self, repo_path=".", author_filters=None, fetch_remote=True):
        self.repo_path = repo_path
        self.author_filters = [f.strip().lower() for f in author_filters] if author_filters else []
        self.fetch_remote = fetch_remote
        self.commits = []
        self.file_stats = []

    def _run_git(self, args):
        try:
            result = subprocess.run(["git"] + args, cwd=self.repo_path, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError:
            return "" 

    def _fetch_latest(self):
        if not self.fetch_remote: return
        try: 
            subprocess.run(["git", "fetch", "--all", "--quiet"], cwd=self.repo_path, capture_output=True, text=True, check=False)
        except Exception: 
            pass

    def _is_my_commit(self, author_name, author_email):
        if not self.author_filters: return True
        return any(f in author_name.lower() or f in author_email.lower() for f in self.author_filters)

    def extract_data(self):
        self._fetch_latest()
        log_format = "--pretty=format:COMMIT_START|%H|%ai|%an|%ae|%s"
        output = self._run_git(["log", log_format, "--numstat", "--no-merges", "--all"])
        if not output: return None

        current_commit = None
        for line in output.splitlines():
            line = line.strip()
            if not line: continue
            if line.startswith("COMMIT_START|"):
                if current_commit and self._is_my_commit(current_commit["author"], current_commit["email"]):
                    self.commits.append(current_commit)
                parts = line.split("|", 5)
                current_commit = {"hash": parts[1][:8], "date": parts[2], "author": parts[3], "email": parts[4], "message": parts[5], "insertions": 0, "deletions": 0}
            elif current_commit and "\t" in line:
                parts = line.split("\t")
                if len(parts) == 3:
                    adds = int(parts[0]) if parts[0] != '-' else 0
                    dels = int(parts[1]) if parts[1] != '-' else 0
                    current_commit["insertions"] += adds
                    current_commit["deletions"] += dels
                    self.file_stats.append({"path": parts[2]})
        if current_commit and self._is_my_commit(current_commit["author"], current_commit["email"]):
            self.commits.append(current_commit)

        if not self.commits: return None

        dates = [datetime.strptime(c["date"].split()[0], "%Y-%m-%d") for c in self.commits]
        return {
            "total_commits": len(self.commits),
            "total_insertions": sum(c["insertions"] for c in self.commits),
            "total_deletions": sum(c["deletions"] for c in self.commits),
            "net_lines": sum(c["insertions"] for c in self.commits) - sum(c["deletions"] for c in self.commits),
            "total_files_touched": len(set(f["path"] for f in self.file_stats)),
            "merges": self._calc_merges(),
            "first_date": min(dates), "last_date": max(dates),
            "timeline": Counter(c["date"].split()[0] for c in self.commits),
            "raw_commits": self.commits,
            "primary_tech": self._get_primary_tech(),
            "packages": self._extract_packages()
        }

    def _calc_merges(self):
        output = self._run_git(["log", "--merges", "--pretty=format:COMMIT_START|%an|%ae", "--all"])
        return sum(1 for line in output.splitlines() if line.startswith("COMMIT_START|") and len(line.split("|")) >= 3 and self._is_my_commit(line.split("|")[1], line.split("|")[2]))

    def _get_primary_tech(self):
        tech = []
        for root, dirs, files in os.walk(self.repo_path):
            if '.git' in root or 'node_modules' in root or 'venv' in root: continue
            if 'package.json' in files:
                try:
                    deps = json.load(open(os.path.join(root, 'package.json'), 'r', encoding='utf-8')).get('dependencies', {})
                    tech.extend([p for p in deps.keys() if any(fw in p.lower() for fw in ['react', 'next', 'vue', 'angular', 'express', 'nestjs', 'tailwind', 'prisma', 'axios'])][:2])
                except: pass
            if 'requirements.txt' in files:
                try:
                    for line in open(os.path.join(root, 'requirements.txt'), 'r', encoding='utf-8'):
                        pkg = re.split(r'[=<>!~]', line.strip())[0].strip()
                        if pkg and any(fw in pkg.lower() for fw in ['django', 'flask', 'fastapi', 'pandas', 'sqlalchemy']): tech.append(pkg)
                except: pass
            if any(f.endswith('.csproj') or f.endswith('.sln') for f in files): tech.append('.NET')
            if any(f == 'go.mod' for f in files): tech.append('Go')
        return ", ".join(list(dict.fromkeys(tech))[:3]) if tech else "Standard Stack"

    def _extract_packages(self):
        packages = set()
        for root, dirs, files in os.walk(self.repo_path):
            if '.git' in root or 'node_modules' in root or 'venv' in root: continue
            if 'package.json' in files:
                try: packages.update(json.load(open(os.path.join(root, 'package.json'), 'r', encoding='utf-8')).get('dependencies', {}).keys())
                except: pass
            if 'requirements.txt' in files:
                try:
                    for line in open(os.path.join(root, 'requirements.txt'), 'r', encoding='utf-8'):
                        line = line.strip()
                        if line and not line.startswith('#') and not line.startswith('-'): packages.add(re.split(r'[=<>!~]', line)[0].strip())
                except: pass
        return sorted(list(packages))[:15]


# ==========================================
# PHASE 2: VISUALIZATION & RENDERING
# ==========================================
def create_heatmap(timeline, start_date, weeks, output_dir, filename, title):
    days_to_monday = start_date.weekday()
    grid_start = start_date - timedelta(days=days_to_monday)
    data = np.zeros((7, weeks))
    current = grid_start
    for week in range(weeks):
        for day in range(7):
            data[day, week] = timeline.get(current.strftime("%Y-%m-%d"), 0)
            current += timedelta(days=1)

    fig, ax = plt.subplots(figsize=(15, 3))
    cmap = mcolors.ListedColormap(["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"])
    ax.pcolormesh(data, cmap=cmap, norm=mcolors.BoundaryNorm([0, 1, 2, 3, 4, 5], cmap.N), edgecolors='#0d1117', linewidth=0.5)
    ax.set_yticks([0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5])
    ax.set_yticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], fontsize=8, color='#8b949e')
    ax.set_xticks([])
    ax.set_facecolor('#0d1117'); fig.patch.set_facecolor('#0d1117')
    for spine in ax.spines.values(): spine.set_visible(False)
    ax.set_title(title, fontsize=12, color='#c9d1d9', pad=10, fontweight='bold')
    plt.savefig(os.path.join(output_dir, filename), dpi=150, bbox_inches='tight', facecolor='#0d1117')
    plt.close()
    return filename


def generate_individual_repo_readme(repo_name, metrics, company_output_dir, company_master_filename):
    """Generates the detailed README and Full History for a SINGLE repo inside its own subfolder."""
    safe_name = re.sub(r'[^\w\-_.]', '_', repo_name)
    
    # Create a dedicated subfolder for this project
    project_output_dir = os.path.join(company_output_dir, safe_name)
    os.makedirs(project_output_dir, exist_ok=True)

    # 1. Generate Heatmaps (inside project folder)
    years = list(range(metrics["first_date"].year, metrics["last_date"].year + 1))
    heatmap_files = []
    for year in years:
        img_name = f"{safe_name}_{year}.png"
        create_heatmap(metrics["timeline"], datetime(year, 1, 1), 52, project_output_dir, img_name, f"Contribution Activity - {year}")
        heatmap_files.append((img_name, year))

    # 2. Generate Full Commit History (inside project folder)
    history_filename = "full_commit_history.md"
    history_path = os.path.join(project_output_dir, history_filename)
    rows = [f"| `{c['hash']}` | {c['date'].split()[0]} | {c['message'].replace('|', '\\|')} | +{c['insertions']} / -{c['deletions']} |" for c in metrics["raw_commits"]]
    
    # CTA: Back to Project Summary (same folder)
    back_to_summary = f"[![⬅️ Back to Project Summary](https://img.shields.io/badge/⬅️_Back_to_Project_Summary-007bff?style=for-the-badge)](README.md)"
    
    with open(history_path, "w", encoding="utf-8") as f:
        f.write(f"# 📜 Full Commit History: {repo_name}\n\n{back_to_summary}\n\n*Total Commits: {len(metrics['raw_commits'])}*\n\n")
        f.write("| Hash | Date | Message | LOC Changes |\n| :--- | :--- | :--- | :--- |\n" + "\n".join(rows))
        f.write("\n\n---\n*Raw metadata only. Zero source code included.*")

    # 3. Generate Individual README (inside project folder)
    readme_path = os.path.join(project_output_dir, "README.md")
    
    # CTA: View Full Commit Log (same folder) & Back to Company Overview (up one level)
    history_link = f"[![📜 View Full Commit Log](https://img.shields.io/badge/_View_Full_Commit_Log-2ea44f?style=for-the-badge)]({history_filename})"
    back_to_company = f"[![ Back to Company Overview](https://img.shields.io/badge/🏢_Back_to_Company_Overview-6e7681?style=for-the-badge)](../{company_master_filename})"
    
    pkg_list = "\n".join([f"- `{p}`" for p in metrics["packages"]]) if metrics["packages"] else "*No major dependencies found.*"
    
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(f"# 📊 {repo_name} - Engineering Impact\n\n")
        f.write(f"{history_link} &nbsp; {back_to_company}\n\n") # Bi-directional navigation
        f.write(f"*Auto-generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Raw metadata, zero code diffs.*\n\n")
        f.write("## 📈 Summary Statistics\n\n| Metric | Value | Metric | Value |\n| :--- | :--- | :--- | :--- |\n")
        f.write(f"| **Total Commits** | `{metrics['total_commits']}` | **Net Lines** | `{metrics['net_lines']}` |\n")
        f.write(f"| **Lines Added** | `+{metrics['total_insertions']}` | **Files Touched** | `{metrics['total_files_touched']}` |\n") 
        f.write(f"| **Lines Removed** | `-{metrics['total_deletions']}` | **Longest Streak** | `N/A` |\n") 
        f.write(f"| **Merges / Reviews** | `{metrics['merges']}` 🤝 | | |\n\n")
        
        f.write("## 🟩 Contribution Graphs\n\n")
        for img, year in heatmap_files: f.write(f"### {year}\n![Graph {year}]({img})\n\n")
        
        f.write("## 📦 Core Packages & Dependencies\n\n" + pkg_list + "\n\n")
        f.write("---\n*Raw metadata only. **Zero source code included for NDA compliance.***")
    
    # Return the relative path from the company root to this project's README
    return f"{safe_name}/README.md"


def generate_master_company_readme(company_name, projects, output_dir, primary_name, global_first, global_last, back_to_url=None):
    """Generates the Master Dashboard linking to all individual repos."""
    safe_name = re.sub(r'[^\w\-_.]', '_', company_name)
    company_master_filename = "README.md"
    
    # Aggregate timelines for the master graph
    combined_timeline = Counter()
    for p in projects:
        combined_timeline.update(p["metrics"]["timeline"])

    # 1. Generate Aggregated Heatmaps (in the root company folder)
    years = list(range(global_first.year, global_last.year + 1))
    heatmap_files = []
    for year in years:
        img_name = f"{safe_name}_Aggregated_{year}.png"
        create_heatmap(combined_timeline, datetime(year, 1, 1), 52, output_dir, img_name, f"Company-Wide Activity ({year})")
        heatmap_files.append((img_name, year))

    # 2. Generate Master README
    readme_path = os.path.join(output_dir, company_master_filename)
    total_commits = sum(p["metrics"]["total_commits"] for p in projects)
    total_merges = sum(p["metrics"]["merges"] for p in projects)
    
    if back_to_url:
        back_to_portfolio = f"[![👤 Back to Main Portfolio](https://img.shields.io/badge/👤_Back_to_Main_Portfolio-58a6ff?style=for-the-badge)]({back_to_url})\n\n"
    else:
        back_to_portfolio = ""

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(f"# 🏢 {company_name} - Engineering Impact\n\n")
        f.write(back_to_portfolio) 
        f.write(f"*Author: `{primary_name}` | Period: {global_first.strftime('%Y-%m-%d')} to {global_last.strftime('%Y-%m-%d')}*\n\n")
        f.write("## 📈 Aggregate Summary Statistics\n\n| Metric | Value |\n| :--- | :--- |\n")
        f.write(f"| **Total Projects** | `{len(projects)}` |\n| **Total Commits** | `{total_commits}` |\n")
        f.write(f"| **Merges / Reviews** | `{total_merges}` 🤝 |\n\n")
        
        f.write("## 🟩 Company-Wide Contribution Graphs\n\n")
        for img, year in heatmap_files: f.write(f"### {year}\n![Graph {year}]({img})\n\n")
        
        f.write("##  Project Breakdown & Navigation\n\n")
        f.write("| Project | Tech Stack | Commits | Merges | Details |\n| :--- | :--- | :--- | :--- | :--- |\n")
        for p in projects:
            m = p["metrics"]
            # The link now points into the subfolder
            details_link = f"[📄 View Summary]({p['readme_file']})"
            f.write(f"| **{p['name']}** | `{m['primary_tech']}` | {m['total_commits']} | {m['merges']} | {details_link} |\n")
            
        f.write("\n---\n*Generated by Corporate Contribution Creator. Raw metadata only. Zero source code included.*")
    print(f"✅ Master Portfolio generated: {readme_path}")


# ==========================================
# PHASE 3: ORCHESTRATION
# ==========================================
def main():
    parser = argparse.ArgumentParser(description="Generate Hierarchical NDA-safe Portfolio.")
    parser.add_argument("--parent-dir", required=True)
    parser.add_argument("--output-dir", default="D:\\Personal\\corporate_history")
    parser.add_argument("--name", required=True)
    parser.add_argument("--author", required=True)
    parser.add_argument("--primary-name", required=True)
    parser.add_argument("--skip-fetch", action="store_true")
    parser.add_argument("--back-to", default=None, help="URL to link back to from the Company Master")
    args = parser.parse_args()
    
    author_filters = [f.strip() for f in args.author.split(',')]
    projects = []
    global_first, global_last = None, None

    print(f"🔍 Recursively scanning {args.parent_dir}...")
    for root, dirs, files in os.walk(args.parent_dir):
        if '.git' in dirs:
            repo_path = root; dirs.remove('.git')
            project_name = os.path.basename(repo_path)
            if project_name.lower() in ['src', 'app', 'web', 'api', 'backend', 'frontend']:
                project_name = os.path.relpath(repo_path, args.parent_dir).replace('\\', '/')
            
            print(f"  Processing: {project_name}")
            extractor = GitMetricsExtractor(repo_path=repo_path, author_filters=author_filters, fetch_remote=not args.skip_fetch)
            metrics = extractor.extract_data()
            
            if metrics:
                projects.append({"name": project_name, "metrics": metrics})
                
                if not global_first or metrics["first_date"] < global_first: global_first = metrics["first_date"]
                if not global_last or metrics["last_date"] > global_last: global_last = metrics["last_date"]

    if not projects:
        print("⚠️ No valid Git repositories with matching commits found."); sys.exit(0)

    # Create a dedicated subfolder for this company to prevent overwriting README.md
    safe_company_name = re.sub(r'[^\w\-_.]', '_', args.name)
    company_output_dir = os.path.join(args.output_dir, safe_company_name)
    os.makedirs(company_output_dir, exist_ok=True)
    print(f"📁 Outputting to dedicated folder: {company_output_dir}")

    # Generate individual repos (they will create their own subfolders inside company_output_dir)
    print("🔗 Generating individual project summaries...")
    for p in projects:
        readme_file = generate_individual_repo_readme(p["name"], p["metrics"], company_output_dir, "README.md")
        p["readme_file"] = readme_file 

    # Generate the master dashboard
    generate_master_company_readme(args.name, projects, company_output_dir, args.primary_name, global_first, global_last, args.back_to)
    
    print("🎉 Hierarchical generation complete!")

if __name__ == "__main__":
    main()